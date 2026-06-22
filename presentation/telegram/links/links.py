"""В файле храним ссылки, которые ведут на другие ресурсы."""
from urllib.parse import quote_plus
import core.config as config

# Документы
DATA_PROCESSING_POLICY = "https://disk.yandex.ru/i/S7m4KlCaBTOHdw"
PUBLIC_OFFER = "https://disk.yandex.ru/i/zs4hvz6Ev8Lxzg"
USER_AGREEMENT = "https://disk.yandex.ru/i/3O2z3CKg19EZgw"

# Бот поддержки
BOT_SUPPORT = "https://t.me/CheburneshkaSupport_bot"

# Формирование ссылок на подписку
def sub_url(token: str) -> str:
    """Универсальная ссылка подписки для v2rayTUN, NekoBox и др."""
    return f"http://{config.SUB_HOST}/sub/{token}"

def happ_deeplink(token: str) -> str:
    """Deeplink для открытия подписки в Happ."""
    return f"happ://add/{sub_url(token)}"

def sub_page(token: str) -> str:
    """Ссылка на сайт с информацией о подписке."""
    return  f"{config.SUB_PROTOCOL}://{config.SUB_HOST}/page/info/{token}"

def happ_redirect(token: str) -> str:
    """Ссылка на сайт с redirect в приложение Happ."""
    return f"{config.SUB_PROTOCOL}://{config.SUB_HOST}/page/{token}"

# IOS
IOS_HAPP = "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
IOS_V2RAYTUN = "https://apps.apple.com/us/app/v2raytun/id6476628951"

# Android
ANDROID_HAPP = "https://play.google.com/store/apps/details?id=com.happproxy"
HUAWEI_HAPP = "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"
ANDROID_V2RAYTUN = "https://play.google.com/store/apps/details?id=com.v2raytun.android"
HUAWEI_V2RAYTUN = "https://github.com/DigneZzZ/v2raytun/releases/download/5.23.73/v2RayTun_universal.apk"

# COMPUTER
COMPUTER_HAPP = "https://www.happ.su/main/ru"
COMPUTER_V2RAYTUN = "https://v2raytun.com/"