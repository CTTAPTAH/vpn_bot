"""
Конструкторы InlineKeyboardMarkup для разных экранов.
Общие кнопки (BTN_MAIN, BTN_BACK) переиспользуются в нескольких клавиатурах.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from application.use_cases.get_available_plans import PlanDTO
from presentation.telegram.enums import Action
from presentation.telegram.states.states import Screen
from presentation.telegram.enums import Platform
from presentation.telegram.texts.plan_presentation import PLAN_PRESENTATION_BY_MONTHS, PlanPresentation
import presentation.telegram.callbacks.callbacks as callbacks
import presentation.telegram.links.links as links
import domain.enums as enums

# Часто используемы кнопки
BTN_BACK = InlineKeyboardButton(text="⬅️ Назад", callback_data=Action.BACK)
BTN_MAIN_MENU = InlineKeyboardButton(text="🏠 Главное меню", callback_data=Action.GO_BACK_TO_MENU)
BTN_SUPPORT = InlineKeyboardButton(text="💬 Поддержка", url=links.BOT_SUPPORT)
BTN_MY_SUB = InlineKeyboardButton(text="📋 Моя подписка", callback_data=Screen.MY_SUB)

# Клавиатура для возврата
def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [BTN_BACK]
        ]
    )
# Клавиатура для ошибки
def kb_error() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [BTN_SUPPORT],
            [BTN_BACK]
        ]
    )

# ===== Главное меню =====
def kb_main(has_trial: bool, is_sub_active: bool, sub_id: int | None) -> InlineKeyboardMarkup:
    buttons = []

    if is_sub_active:
        buttons.append([InlineKeyboardButton(
            text="🔄 Продлить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.RENEW, sub_id=sub_id).pack()
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="💳 Купить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.CREATE).pack()
        )])

    if has_trial:
        buttons.append([InlineKeyboardButton(text="🎁 Пробный период", callback_data=Screen.TRIAL)])

    buttons.append([BTN_MY_SUB])
    buttons.append([BTN_SUPPORT])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_agreement() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data=Action.AGREE)]
    ])

def kb_view_agreement() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_BACK]
    ])

# Тарифы, покупка
def kb_plans(action: enums.PaymentAction, plans: list[PlanDTO],
             *, sub_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = []

    for plan in plans:
        presentation = PLAN_PRESENTATION_BY_MONTHS.get(plan.duration_months, PlanPresentation("", ""))
        text = f"{presentation.emoji} {plan.name} — {plan.price} ₽"
        buttons.append([InlineKeyboardButton(
                text=text,
                callback_data=callbacks.PurchasePendingCallback(action=action, plan_id=plan.id, sub_id=sub_id).pack()
            )])
    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_purchase_pending(payment_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_link)],
        [BTN_BACK]
    ])

def kb_purchase_success(sub_token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="📱 Открыть в Happ", url=links.happ_deeplink(sub_token))],
        #[InlineKeyboardButton(text="📱 Открыть в v2rayTUN", url=links.sub_url(sub_token))],
        [InlineKeyboardButton(text="❓ Как подключиться", callback_data=Screen.INSTRUCTION)],
        [BTN_MY_SUB],
        [BTN_MAIN_MENU]
    ])

def kb_renew_success() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_MY_SUB],
        [BTN_MAIN_MENU]
    ])

def kb_purchase_canceled() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_MAIN_MENU]
    ])

# Пробный период
def kb_trial(sub_token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="📱 Открыть в Happ", url=links.happ_redirect(sub_token))],
        [InlineKeyboardButton(text="❓ Как подключиться", callback_data=Screen.INSTRUCTION)],
        [BTN_MY_SUB],
        [BTN_MAIN_MENU]
    ])

# Моя подписка
def kb_my_sub(sub_token: str | None, sub_id: int | None) -> InlineKeyboardMarkup:
    buttons = []

    if sub_token is not None:
        #buttons.append([InlineKeyboardButton(text="📱 Открыть в Happ", url=links.happ_redirect(sub_token))])
        pass

    if sub_token is None:
        buttons.append([InlineKeyboardButton(
            text="💳 Купить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.CREATE).pack()
        )])

    if sub_token is not None:
        buttons.append([InlineKeyboardButton(text="❓ Как подключиться", callback_data=Screen.INSTRUCTION)])
        buttons.append([InlineKeyboardButton(
            text="🔄 Продлить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.RENEW, sub_id=sub_id).pack()
        )])

    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== Инструкции =====
def kb_instruction() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Телефон", callback_data=Screen.PHONE)],
        [InlineKeyboardButton(text="💻 Компьютер", callback_data=Screen.COMPUTER)],
        [InlineKeyboardButton(text="📺 Телевизор", callback_data=Screen.TV)],
        [BTN_BACK],
    ])

# Happ
def kb_happ_setup(platform: Platform) -> InlineKeyboardMarkup:
    download_url = _get_happ_download_url(platform)
    problems_screen = _get_problems_screen(platform)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать Happ", url=download_url)],
        [InlineKeyboardButton(text="❓ Не получается?", callback_data=problems_screen)],
        [BTN_SUPPORT],
        [BTN_BACK],
    ])
def _get_problems_screen(platform: Platform) -> Screen:
    match platform:
        case Platform.IPHONE:
            return Screen.PROBLEM_IPHONE
        case Platform.ANDROID:
            return Screen.PROBLEM_ANDROID
        case Platform.HUAWEI:
            return Screen.PROBLEM_HUAWEI
        case Platform.APPLE_TV:
            return Screen.PROBLEM_APPLE_TV
        case Platform.ANDROID_TV:
            return Screen.PROBLEM_ANDROID_TV
        case Platform.COMPUTER:
            return Screen.PROBLEM_COMPUTER
        case _:
            raise ValueError(f"Unknown platform: {platform}")
def _get_happ_download_url(platform: Platform) -> str:
    match platform:
        case Platform.IPHONE | Platform.APPLE_TV:
            return links.IOS_HAPP
        case Platform.ANDROID | Platform.ANDROID_TV:
            return links.ANDROID_HAPP
        case Platform.HUAWEI:
            return links.HUAWEI_HAPP
        case Platform.COMPUTER:
            return links.COMPUTER_HAPP
        case _:
            raise ValueError(f"Unknown platform: {platform}")

# v2rayTun
def kb_v2raytun_setup(platform: Platform) -> InlineKeyboardMarkup:
    download_url = _get_v2raytun_download_url(platform)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать v2rayTun", url=download_url)],
        [BTN_SUPPORT],
        [BTN_BACK],
    ])
def _get_v2raytun_download_url(platform: Platform) -> str:
    match platform:
        case Platform.IPHONE | Platform.APPLE_TV:
            return links.IOS_V2RAYTUN
        case Platform.ANDROID | Platform.ANDROID_TV:
            return links.ANDROID_V2RAYTUN
        case Platform.HUAWEI:
            return links.HUAWEI_V2RAYTUN
        case Platform.COMPUTER:
            return links.COMPUTER_V2RAYTUN
        case _:
            raise ValueError(f"Unknown platform: {platform}")

# Телефон
def kb_phone() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍎 iPhone", callback_data=Screen.IPHONE)],
        [InlineKeyboardButton(text="🤖 Android", callback_data=Screen.ANDROID)],
        [InlineKeyboardButton(text="🌸 Huawei", callback_data=Screen.HUAWEI)],
        [BTN_BACK],
    ])

# Телевизор
def kb_tv() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍎 Apple TV", callback_data=Screen.APPLE_TV)],
        [InlineKeyboardButton(text="🤖 Android TV", callback_data=Screen.ANDROID_TV)],
        [BTN_BACK],
    ])