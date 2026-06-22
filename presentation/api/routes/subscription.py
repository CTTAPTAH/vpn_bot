import base64
from fastapi import APIRouter, Response
from app.container import build_uow
from application.use_cases.get_subscription import GetSubscriptionUseCase

router = APIRouter()

@router.get("/sub/{token}")
async def get_subscription(token: str):
    use_case = GetSubscriptionUseCase(build_uow())
    result = await use_case.execute(token)

    if not result.success:
        return Response(status_code=404)

    content = "\n".join(result.vless_links)
    encoded = base64.b64encode(content.encode()).decode()
    return Response(content=encoded, media_type="text/plain")