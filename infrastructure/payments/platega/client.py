"""
Реализация провайдера кассы через сервис platega.

Используется в application-слое через абстракцию.
"""
import asyncio, httpx, logging
from datetime import timedelta

from application.ports.payment_provider import AbstractPaymentProvider, PaymentData, TransactionStatus
from infrastructure.http.http_client import HttpClient
from infrastructure.http.http_client import HttpConnectionError, HttpTimeoutError
from domain.enums import PaymentMethod
import core.config as config

logger = logging.getLogger(__name__)

class PlategaClient(AbstractPaymentProvider):
    def __init__(self, http_client: HttpClient):
        self._http: HttpClient = http_client

    @property
    def _auth_headers(self) -> dict:
        return {
            "X-MerchantId": config.PLATEGA_MERCHANT_ID,
            "X-Secret": config.PLATEGA_API_KEY
        }

    def _parse_expires_in(self, value: str | None) -> timedelta | None:
        if not value:
            return None

        parts = value.split(":")
        if len(parts) != 3:
            return None

        h, m, s = map(int, parts)
        return timedelta(hours=h, minutes=m, seconds=s)

    async def start(self):
        await self._http.start()

    async def close(self):
        await self._http.close()

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        attempt = 0
        delay = config.PLATEGA_RETRY_BASE_DELAY

        while attempt < config.PLATEGA_RETRY_ATTEMPTS:
            try:
                if method.lower() == "get":
                    response = await self._http.get(url, **kwargs)
                elif method.lower() == "post":
                    response = await self._http.post(url, **kwargs)
                else:
                    raise Exception("Unknow method")

                if response.status_code != 200:
                    logger.error("Platega returned error: %s", response.text)
                    raise Exception("Platega returned non-200 response")
                return response

            except (HttpConnectionError, HttpTimeoutError) as e:
                attempt += 1
                logger.warning(
                    "Platega connection error: %s. Attempt %d/%d",
                    e, attempt, config.PLATEGA_RETRY_ATTEMPTS
                )
                if attempt >= config.PLATEGA_RETRY_ATTEMPTS:
                    logger.error("Platega retry limit exceeded")
                    raise

                await asyncio.sleep(delay)
                delay *= config.PLATEGA_RETRY_MULTIPLIER

        raise RuntimeError("Unexpected exit from retry loop")

    async def create_payment(self, payment_method: PaymentMethod, amount: float,
                             currency: str, description: str) -> PaymentData:
        payload = {
            "paymentMethod": int(payment_method),
            "paymentDetails": {
                "amount": amount,
                "currency": currency
            },
            "description": description
        }

        response: httpx.Response = await self._request_with_retry(
            "post",
            "/transaction/process",
            json=payload,
            headers=self._auth_headers
        )

        data = response.json()
        transaction_id = data["transactionId"]
        redirect_url = data.get("redirect")

        return PaymentData(
            transaction_id=transaction_id,
            redirect_url=redirect_url
        )

    async def get_transaction_status(self, transaction_id: str) -> TransactionStatus:
        response: httpx.Response = await self._request_with_retry(
            "get",
            f"/transaction/{transaction_id}",
            headers=self._auth_headers
        )
        data = response.json()

        return TransactionStatus(
            transaction_id=data["id"],
            status=data["status"],
            amount=data["paymentDetails"]["amount"],
            currency=data["paymentDetails"]["currency"],
            payment_method=data["paymentMethod"],
            expires_in=self._parse_expires_in(data["expiresIn"]),
            external_id=data["externalId"]
        )

    async def is_payment_expiring_soon(self, transaction_id: str, threshold_minutes: int) -> bool:
        status = await self.get_transaction_status(transaction_id)
        if status is None:
            return True

        # если нет expiresIn - НЕ делаем вывод
        if status.expires_in is None:
            return False

        return status.expires_in < timedelta(minutes=threshold_minutes)