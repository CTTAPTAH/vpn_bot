"""
Конструкторы InlineKeyboardMarkup для разных экранов.
Общие кнопки (BTN_MAIN, BTN_BACK) переиспользуются в нескольких клавиатурах.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from application.use_cases.get_available_plans import PlanDTO
from application.common.dto import KeyDTO
from presentation.telegram.enums import Action
from presentation.telegram.states.states import Screen
from presentation.telegram.texts.plan_presentation import PLAN_PRESENTATION_BY_MONTHS, PlanPresentation
import presentation.telegram.callbacks.callbacks as callbacks
import presentation.telegram.links.links as links
import domain.enums as enums

# Часто используемы кнопки
BTN_BACK = InlineKeyboardButton(text="⬅️ Назад", callback_data=Action.BACK)
BTN_MAIN_MENU = InlineKeyboardButton(text="🏠 Главное меню", callback_data=Action.GO_BACK_TO_MENU)
BTN_HELP = InlineKeyboardButton(text="💬 Поддержка", callback_data=Screen.HELP)
BTN_MY_KEYS = InlineKeyboardButton(text="🔑 Мои ключи", callback_data=Screen.MY_KEYS)

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
            [BTN_HELP],
            [BTN_BACK]
        ]
    )

# ===== Главное меню =====
def kb_main(has_trial: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="💳 Купить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.CREATE).pack()
        )],
        [BTN_MY_KEYS]
    ]

    if has_trial:
        buttons.append([InlineKeyboardButton(text="🎁 Пробный период", callback_data=Screen.TRIAL)])

    buttons.append(
        [InlineKeyboardButton(text="📱 Настроить защищённое подключение", callback_data=Screen.INSTRUCTION)]
    )
    buttons.append([BTN_HELP])
    buttons.append([InlineKeyboardButton(text="📄 Оферта / Политика", callback_data=Screen.VIEW_AGREEMENT)])

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
             pending_payment_id: int, *, key_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = []

    for plan in plans:
        presentation = PLAN_PRESENTATION_BY_MONTHS.get(plan.duration_months, PlanPresentation("", ""))
        text = f"{presentation.emoji} {plan.name} — {plan.price} ₽"
        buttons.append([InlineKeyboardButton(
                text=text,
                callback_data=callbacks.PurchasePendingCallback(action=action, plan_id=plan.id, key_id=key_id).pack()
            )])
    if pending_payment_id is not None:
        buttons.append([InlineKeyboardButton(
            text="💳 Продолжить оплату",
            callback_data=callbacks.PurchasePendingCallback(
                action=action,
                plan_id=pending_payment_id,
                key_id=key_id).pack()
        )])
    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_purchase_pending(payment_link: str, action: enums.PaymentAction,
                        payment_id: int, *, key_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_link)],
        [InlineKeyboardButton(text="✅ Проверить доступ", callback_data=callbacks.PurchaseSuccessCallback(
            action=action,
            payment_id=payment_id,
            key_id=key_id
        ).pack())],
        [InlineKeyboardButton(text="❌ Отменить платёж", callback_data=callbacks.CancelPaymentCallback(
            payment_id=payment_id
        ).pack())],
        [BTN_BACK]
    ])

def kb_purchase_success() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Продолжить", callback_data=Screen.INSTRUCTION)],
        [BTN_MY_KEYS],
        [BTN_MAIN_MENU]
    ])


# Пробный период
def kb_trial() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Перейти к инструкции", callback_data=Screen.INSTRUCTION)],
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_trial_limit(keys: list[KeyDTO]) -> InlineKeyboardMarkup:
    buttons = []

    # кнопки тарифов
    for i, key in enumerate(keys, start=1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i}. {key.plan_name}",
                callback_data=callbacks.ExtendTrialCallback(key_id=key.id).pack()
            )
        ])

    # помощь и назад
    buttons.append([BTN_HELP])
    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_extend_trial() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Инструкция", callback_data=Screen.INSTRUCTION)],
        [BTN_MY_KEYS],
        [BTN_MAIN_MENU],
    ])

# Мои ключи
def kb_my_keys(keys: list[KeyDTO]) -> InlineKeyboardMarkup:
    buttons = []

    for i, key in enumerate(keys, start=1):
        emoji = "🔴" if key.is_expired else "🟢"
        date = key.end_at.strftime("%d.%m")

        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} Ключ {i} до {date}",
                callback_data=callbacks.SelectedKeyCallback(key_id=key.id).pack()
            )
        ])
    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_selected_key(key_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Инструкция подключения", callback_data=Screen.INSTRUCTION)],
        [InlineKeyboardButton(
            text="💳 Продлить доступ",
            callback_data=callbacks.PlansCallback(action=enums.PaymentAction.RENEW, key_id=key_id).pack()
        )],
        [InlineKeyboardButton(
            text="🗑 Удалить ключ",
            callback_data=callbacks.ConfirmDeleteKeyCallback(key_id=key_id).pack()
        )],
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_confirm_delete_key(key_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=callbacks.DeleteKeyCallback(key_id=key_id).pack()
        )],
        [InlineKeyboardButton(text="⬅️ Вернуться к ключу", callback_data=Action.BACK)]
    ])

# Поддержка
def kb_help() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Часто задаваемый вопросы", callback_data=Screen.FAQ)],
        [InlineKeyboardButton(text="Написать запрос", callback_data=Screen.REQUEST_HELP)],
        [InlineKeyboardButton(text="Мои обращения", callback_data=Screen.MY_REQUESTS)],
        [BTN_BACK]
    ])

def kb_faq() -> InlineKeyboardMarkup:
    return kb_back()

def kb_request_help() -> InlineKeyboardMarkup:
    return kb_back()

def kb_my_requests() -> InlineKeyboardMarkup:
    return kb_back()

# ===== Инструкции =====
def kb_instruction() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apple", callback_data=Screen.APPLE)],
        [InlineKeyboardButton(text="Android", callback_data=Screen.ANDROID)],
        [InlineKeyboardButton(text="Windows", callback_data=Screen.WINDOWS)],
        [InlineKeyboardButton(text="TV", callback_data=Screen.TV)],
        [InlineKeyboardButton(text="HUAWEI", callback_data=Screen.HUAWEI)],
        [BTN_BACK]
    ])

# APPLE
def kb_apple(vless_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить приложение", url=links.APPLE_V2RAY_APP)],
        [InlineKeyboardButton(text="Подключиться", url=links.v2raytun_ios_link(vless_link))],
        [InlineKeyboardButton(text="Возникли проблемы", callback_data=Screen.PROBLEMS_APPLE)],
        [InlineKeyboardButton(text="2-й способ подключения", callback_data=Screen.SECOND_METHOD_APPLE)],
        [BTN_BACK]
    ])

def kb_problems_apple() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Если подключение не установлено", callback_data=Screen.NO_CONNECTION_APPLE)],
        [BTN_HELP],
        [BTN_MY_KEYS],
        [BTN_BACK]
    ])

def kb_no_connection_apple() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_second_method_apple() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"Happ Global\"", url=links.APPLE_HAPP_GLOBAL)],
        [InlineKeyboardButton(text="Установить \"Happ RU\"", url=links.APPLE_HAPP_RU)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

# ANDROID
def kb_android(vless_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить приложение", url=links.APPLE_V2RAY_APP)],
        [InlineKeyboardButton(text="Подключиться", url=links.v2raytun_android_link(vless_link))],
        [InlineKeyboardButton(text="Возникли проблемы", callback_data=Screen.PROBLEMS_ANDROID)],
        [InlineKeyboardButton(text="2-й способ подключения", callback_data=Screen.SECOND_METHOD_ANDROID)],
        [BTN_BACK]
    ])

def kb_problems_android() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Если подключение не установлено", callback_data=Screen.NO_CONNECTION_ANDROID)],
        [BTN_HELP],
        [BTN_MY_KEYS],
        [BTN_BACK]
    ])

def kb_no_connection_android() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_second_method_android() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"Happ\"", url=links.ANDROID_HAPP)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

# WINDOWS
def kb_windows() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Защищённое подключение для отдельных приложений/сайтов", callback_data=Screen.PC_APPS)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_pc_apps() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"AmneziaVPN\"", url=links.WINDOWS_AMNEZIA_APP)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

# TV
def kb_tv() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Android TV", callback_data=Screen.ANDROID_TV)],
        [InlineKeyboardButton(text="Apple TV", callback_data=Screen.APPLE_TV)],
        [BTN_BACK]
    ])

def kb_android_tv() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"V2RayTun\"", url=links.APPLE_V2RAY_APP)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_apple_tv() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"V2RayTun\"", url=links.APPLE_TV_SHADOWROCKET)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])

# HUAWEI
def kb_huawei() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить приложение", url=links.HUAWEI_V2RAYTUN)],
        [BTN_MY_KEYS],
        [InlineKeyboardButton(text="2-й способ подключения", callback_data=Screen.SECOND_METHOD_HUAWEI)],
        [BTN_HELP],
        [BTN_BACK]
    ])

def kb_second_method_huawei() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить \"Happ\"", url=links.HUAWEI_HAPP)],
        [BTN_MY_KEYS],
        [BTN_HELP],
        [BTN_BACK]
    ])