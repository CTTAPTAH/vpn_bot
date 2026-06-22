from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import core.config as config
from core.utils import utcnow
from app.container import build_uow

router = APIRouter()
templates = Jinja2Templates(directory="presentation/api/templates")

@router.get("/page/info/{token}", response_class=HTMLResponse)
async def subscription_page(request: Request, token: str):
    sub_url = f"{config.SUB_PROTOCOL}://{config.SUB_HOST}/sub/{token}"
    happ_url = f"happ://add/{sub_url}"

    async with build_uow() as uow:
        sub = await uow.sub.get_by_token(token)
        if sub:
            keys = await uow.keys.list_by_sub(sub.id)
            vless_links = [key.vless_link for key in keys if key.vless_link]
        else:
            vless_links = []

    is_active = sub is not None and sub.end_at > utcnow()
    sub_end_at = sub.end_at.isoformat() if sub else None

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "subscription_url": sub_url,
            "happ_url": happ_url,
            "is_active": is_active,
            "sub_end_at": sub_end_at,
            "max_devices": config.MAX_DEVICE_PER_KEY,
            "vless_links": vless_links,
            "servers_count": len(vless_links),
        }
    )

@router.get("/page/{token}", response_class=HTMLResponse)
async def subscription_redirect(request: Request, token: str):
    sub_url = f"{config.SUB_PROTOCOL}://{config.SUB_HOST}/sub/{token}"
    happ_url = f"happ://add/{sub_url}"

    # Простая страница которая сразу редиректит в Happ
    return templates.TemplateResponse(
        request=request,
        name="redirect.html",
        context={
            "happ_url": happ_url
        }
    )