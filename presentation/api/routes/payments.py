import logging
from fastapi import APIRouter, Request, HTTPException

import core.config as config
from app.container import build_uow, get_vpn_gateway_factory
from application.use_cases.confirm_payment import ConfirmPaymentUseCase
from application.use_cases.handle_failed_payment import HandleFailedPaymentUseCase
from application.services.server_selection import ServerSelectionService
from presentation.telegram.bot import bot
import presentation.telegram.texts.texts as texts
import presentation.telegram.keyboards.keyboards as keyboards
from presentation.telegram.states.manager import state_manager
from presentation.telegram.states.states import Screen
from presentation.telegram.screens.screens import PurchaseSuccessData
from domain.enums import PaymentProvider, PaymentAction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/platega/webhook")
async def platega_webhook(requset: Request):
    # Проверка headers
    merchant_id = requset.headers.get("X-MerchantId")
    secret = requset.headers.get("X-Secret")

    if merchant_id != config.PLATEGA_MERCHANT_ID or secret != config.PLATEGA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid webhook headers")

    # Чтение тела
    data = await requset.json()

    try:
        transaction_id = data["id"]
        status = data["status"]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    logger.info(f"Webhook received: status={status}, transaction_id={transaction_id}")

    # Вызвать use_case
    if status == "CONFIRMED":
        logger.info(f"Payment confirmed: {transaction_id}")

        use_case = ConfirmPaymentUseCase(build_uow(), get_vpn_gateway_factory(), ServerSelectionService())
        dto = await use_case.execute(PaymentProvider.PLATEGA, transaction_id)

        if dto.success:
            keyboard = keyboards.kb_purchase_success()

            if dto.payment_action is PaymentAction.CREATE:
                text = texts.txt_purchase_success(dto.vless_link)
            elif dto.payment_action is PaymentAction.RENEW:
                text = texts.txt_renew_success(dto.vless_link)
            else:
                text = texts.txt_unknown_error()

        else:
            logger.error(f"Use case failed: {dto.error}, transaction_id={transaction_id}")
            keyboard = keyboards.kb_error()
            text = texts.txt_unknown_error()

    elif status == "CANCELED":
        logger.info(f"Payment canceled: {transaction_id}")

        use_case = HandleFailedPaymentUseCase(build_uow())
        dto = await use_case.execute(PaymentProvider.PLATEGA, transaction_id)

        if dto.success:
            keyboard = keyboards.kb_error()
            text = texts.txt_payment_cancelled()
        else:
            logger.error(f"Use case failed: {dto.error}, transaction_id={transaction_id}")
            keyboard = keyboards.kb_error()
            text = texts.txt_unknown_error()

    else:
        logger.warning(f"Unknown payment status: {status}, transaction_id={transaction_id}")
        return {"ok": True}

    # Вывод сообщения пользователю и очистка стека состояний
    if dto.tg_chat_id and dto.tg_message_id and dto.tg_user_id:
        # Очистка стека состояний
        state_manager.reset_state(dto.tg_user_id)
        state_manager.push_state(dto.tg_user_id, Screen.MAIN)
        if status == "CONFIRMED":
            assert dto.payment_action is not None
            state_manager.push_state(
                dto.tg_user_id,
                Screen.PURCHASE_SUCCESS,
                PurchaseSuccessData(
                    provider=PaymentProvider.PLATEGA,
                    payment_provider_id=transaction_id,
                    payment_action=dto.payment_action,
                    vless_link=dto.vless_link
                )
            )
        else:
            state_manager.push_state(
                dto.tg_user_id,
                Screen.PURCHASE_CANCELED
            )

        try:
            await bot.edit_message_text(
                chat_id=dto.tg_chat_id,
                message_id=dto.tg_message_id,
                text=text,
                reply_markup=keyboard
            )
            return {"ok": True}
        except Exception:
            pass

    if dto.tg_chat_id is not None:
        await bot.send_message(
            chat_id=dto.tg_chat_id,
            text=text,
            reply_markup=keyboard
        )
    else:
        logger.error(
            f"Cannot notify user: missing tg_chat_id. "
            f"transaction_id={transaction_id}, status={status}, dto={dto}"
        )

    return {"ok": True}