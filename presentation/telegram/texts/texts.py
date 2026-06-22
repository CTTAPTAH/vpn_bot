"""
Тексты, которые используются в боте при составлении сообщения
"""
from datetime import datetime

import presentation.telegram.texts.branding as branding
import presentation.telegram.links.links as links
from presentation.telegram.enums import Platform
from presentation.telegram.texts.plan_presentation import PLAN_PRESENTATION_BY_MONTHS, PlanPresentation
from application.use_cases.get_available_plans import PlanDTO
import core.utils as utils

def txt_unknown_error() -> str:
    return """⚠️ <b>Произошла ошибка</b>

Не удалось выполнить действие. Попробуйте ещё раз.

Если проблема повторится — обратитесь в поддержку."""

# ===== Главное меню =====
def txt_main(sub_end_at: datetime | None, is_sub_active: bool) -> str:
    text = f"🚀 <b>{branding.VPN_NAME}</b>\n\nБезопасное и стабильное подключение.\n\n"

    if is_sub_active:
        formatted = utils.format_date_ru(sub_end_at)
        status = f"✅ Подписка активна до {formatted}"
    elif sub_end_at is not None:
        formatted = utils.format_date_ru(sub_end_at)
        status = f"⚠️ Подписка истекла {formatted}"
    else:
        status = "❌ Подписки нет"

    text += f"{status}"

    return text

def txt_agreement() -> str:
    return f"""📄 <b>Политика обработки персональных данных и оферта</b>

Перед использованием <b>{branding.VPN_NAME}</b> необходимо ознакомиться с нашими документами и подтвердить согласие:


- <a href="{links.DATA_PROCESSING_POLICY}">Политика обработки персональных данных</a>
- <a href="{links.PUBLIC_OFFER}">Оферта</a>
- <a href="{links.USER_AGREEMENT}">Пользовательское соглашение</a>

Нажмите ✅ ниже, если вы согласны с условиями и хотите продолжить использование бота."""

def txt_view_agreement() -> str:
    return f"""📄 <b>Политика обработки персональных данных и оферта</b>

Вы можете в любой момент ознакомиться с документами <b>{branding.VPN_NAME}</b>:

- <a href="{links.DATA_PROCESSING_POLICY}">Политика обработки персональных данных</a>
- <a href="{links.PUBLIC_OFFER}">Оферта</a>
- <a href="{links.USER_AGREEMENT}">Пользовательское соглашение</a>"""

# Тарифы, покупка
def txt_plans(plans: list[PlanDTO]) -> str:
    text = "<b>💳 Выберите тариф подключения</b>\n"
    text += "<blockquote>Выберите удобный срок и цену</blockquote>\n\n"

    for plan in plans:
        # Получение презентационных данных месяца
        presentation = PLAN_PRESENTATION_BY_MONTHS.get(plan.duration_months, PlanPresentation("", ""))

        # Эмодзи + название
        line = f"{presentation.emoji} <b>{plan.name}</b>\n"

        # Цена
        line += f"<blockquote><b>{plan.price} ₽</b></blockquote>\n"

        # Цена за месяц (если больше 1 месяца)
        if plan.duration_months > 1:
            line += f"({plan.price // plan.duration_months} ₽ / месяц)\n"

        # Описание
        if presentation.description:
            line += f"{presentation.description}\n"

        text += line + "\n"

    return text

def txt_purchase_pending(plan_name: str, price: int) -> str:
    return f"""💳 <b>Вы выбрали тариф: {plan_name}</b>

Сумма к оплате: <b>{price} ₽</b>

Нажмите кнопку ниже, чтобы перейти к оплате.

После подтверждения оплаты используйте кнопку «Проверить доступ», чтобы получить данные для подключения."""

def txt_purchase_success(sub_token: str) -> str:
    return f"""✅ <b>Оплата прошла успешно!</b>

Ваша подписка активирована. Подключитесь через приложение:

Ссылка для v2rayTUN и других:
<pre>{links.sub_url(sub_token)}</pre>

Ссылка для Happ:
<pre>{links.happ_deeplink(sub_token)}</pre>

⚠️ Для Happ используйте кнопку ниже."""

def txt_renew_success() -> str:
    return """🔁 <b>Доступ успешно продлён!</b>

Подписка продлена — ничего перенастраивать не нужно, приложение обновится автоматически."""

def txt_payment_cancelled() -> str:
    return """❌ <b>Платёж отменён</b>

Оплата не была завершена. Попробуйте снова."""

# Пробный период
def txt_trial_created(sub_end_at: datetime, sub_token: str) -> str:
    formatted = utils.format_date_ru(sub_end_at)
    return f"""🎁 <b>Пробный период активирован!</b>

Бесплатный доступ выдан до {formatted}.

Ссылка для v2rayTUN и других:
<pre>{links.sub_url(sub_token)}</pre>

Ссылка для Happ:
<pre>{links.happ_deeplink(sub_token)}</pre>

Подключитесь через приложение 👇"""

def txt_trial_renewed(sub_end_at: datetime, sub_token: str) -> str:
    formatted = utils.format_date_ru(sub_end_at)
    return f"""🎁 <b>Подписка продлена пробным периодом!</b>

Доступ активен до {formatted}.

Ссылка redirect Happ:
<pre>{links.happ_redirect(sub_token)}</pre>

Ссылка для сайта:
<pre>{links.sub_page(sub_token)}</pre>"""

# Моя подписка
def txt_my_sub(sub_end_at: datetime | None, is_sub_active: bool, sub_token: str | None) -> str:
    text = "📋 <b>Моя подписка</b>\n\n"

    if is_sub_active:
        formatted = utils.format_date_ru(sub_end_at)
        status = f"Статус: ✅ Активна до {formatted}"
    elif sub_end_at is not None:
        formatted = utils.format_date_ru(sub_end_at)
        status = f"Статус: ⚠️ Истекла {formatted}"
    else:
        status = "❌ Подписки нет"

    text += f"{status}\n\n"

    if sub_token is not None:
        text += (
            f"Ссылка для подключения:\n"
            f"""Ссылка redirect Happ:
<pre>{links.happ_redirect(sub_token)}</pre>

Ссылка для сайта:
<pre>{links.sub_page(sub_token)}</pre>"""
        )
    else:
        text += "Приобретите доступ, чтобы начать пользоваться VPN 👇"

    return text

# ===== Инструкции =====
def txt_instruction() -> str:
    return (
        "🔒 <b>Подключение</b>\n\n"
        "Выберите устройство:"
    )

# Общая инструкция для Happ
def txt_happ_setup(platform: Platform, token: str) -> str:
    title = _get_platform_title(platform)
    link = links.happ_deeplink(token)
    return (
        f"{title}\n\n"
        "1. Скачайте Happ\n"
        "2. Нажмите «Подключиться» ниже\n"
        "3. Откройте Happ и включите VPN\n\n"
        f"<pre>{link}</pre>\n\n"
        "Готово ✅"
    )
# Общая инструкция для v2rayTun
def txt_v2raytun_setup(platform: Platform, token: str) -> str:
    title = _get_platform_title(platform)
    link = links.sub_url(token)

    return (
        f"{title}\n\n"
        "Если Happ не подошёл, попробуйте v2rayTun:\n\n"
        "1. Скачайте v2rayTun\n"
        "2. Скопируйте ссылку ниже\n"
        "3. В приложении нажмите «+» → «Импорт из буфера обмена»\n\n"
        f"<pre>{link}</pre>\n\n"
        "Готово ✅"
    )
def _get_platform_title(platform: Platform) -> str:
    match platform:
        case Platform.IPHONE:
            return "🍎 iPhone"
        case Platform.ANDROID:
            return "🤖 Android"
        case Platform.HUAWEI:
            return "🌸 Huawei"
        case Platform.APPLE_TV:
            return "🍎 Apple TV"
        case Platform.ANDROID_TV:
            return "🤖 Android TV"
        case Platform.COMPUTER:
            return "💻 Компьютер"
        case _:
            raise ValueError(f"Unknown platform: {platform}")

# Телефон
def txt_phone() -> str:
    return (
        "📱 <b>Телефон</b>\n\n"
        "Выберите вашу систему:"
    )

# Телевизор
def txt_tv() -> str:
    return (
        "📺 <b>Телевизор</b>\n\n"
        "Выберите вашу систему:"
    )