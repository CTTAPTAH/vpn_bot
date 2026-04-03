"""В файле храним ссылки, которые ведут на другие ресурсы."""
from urllib.parse import quote_plus

# Документы
DATA_PROCESSING_POLICY = "https://disk.yandex.ru/i/S7m4KlCaBTOHdw"
PUBLIC_OFFER = "https://disk.yandex.ru/i/zs4hvz6Ev8Lxzg"

# Deeplink
VPN_HOST = "171.22.30.206"
def v2raytun_deeplink(vless: str) -> str:
    """Генерирует deeplink для  v2RayTun."""
    inner = quote_plus(vless)
    return f"v2raytun://import?url={inner}"

# Apple
APPLE_V2RAY_APP = "https://apps.apple.com/ru/app/v2raytun/id6476628951"
APPLE_V2BOX_APP = "https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690"
APPLE_HAPP_GLOBAL ="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"
APPLE_HAPP_RU = "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
def v2raytun_ios_link(vless: str) -> str:
    """Используется в боте для кнопки "Настроить соединение" для IOS."""
    deeplink = quote_plus(v2raytun_deeplink(vless))
    return f"https://{VPN_HOST}/redirect_ios.html?deeplink={deeplink}"

# Android
ANDROID_V2RAY_APP = "https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru&ysclid=mkp8j454tn760580671"
ANDROID_V2BOX_APP = "https://play.google.com/store/apps/details/V2Box+-+V2ray+Client?id=dev.hexasoftware.v2box&hl=ru&ysclid=mkp8ifanmc128980019"
ANDROID_HAPP = "https://play.google.com/store/apps/details?id=com.happproxy"
def v2raytun_android_link(vless: str) -> str:
    """Используется в боте для кнопки "Настроить соединение" для Android."""
    deeplink = quote_plus(v2raytun_deeplink(vless))
    return f"https://{VPN_HOST}/redirect_android.html?deeplink={deeplink}"

# Windows
WINDOWS_NEKORAY_APP = "https://github.com/MatsuriDayo/nekoray/releases"
WINDOWS_AMNEZIA_APP = "https://amnezia.org/ru/downloads"

# Apple TV
APPLE_TV_SHADOWROCKET = "https://apps.apple.com/ua/app/shadowrocket/id932747118?l=ru&platform=tv"

# HUAWEI
HUAWEI_V2RAYTUN = "https://apkpure.net/ru/v2raytun-app/com.v2raytun.android?ysclid=ml24n1u09w793029480"
HUAWEI_HAPP = "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"