"""
Функции отображения экранов бота.

Экранные функции (show_xxx) – отвечают за отображение текста и клавиатур.
Используются в process_back() и при переключении между разделами.
"""
from aiogram import types
from typing import Callable, Awaitable
from dataclasses import dataclass
from domain.enums import PaymentProvider

from app.container import get_vpn_gateway_factory, build_uow, get_platega_client
from application.use_cases.get_main_menu import GetMainMenuUseCase
from application.use_cases.get_available_plans import GetAvailablePlansUseCase
from application.use_cases.create_payment import CreatePaymentUseCase
from application.use_cases.activate_trial import ActivateTrialUseCase
from application.use_cases.get_user_sub import GetUserSubUseCase
from presentation.telegram.states.states import Screen
import presentation.telegram.texts.texts as texts
import presentation.telegram.keyboards.keyboards as keyboards
import presentation.telegram.callbacks.callbacks as callbacks
from presentation.telegram.enums import Platform
import domain.enums as enums
import core.config as config

@dataclass
class PurchaseSuccessData:
    """Структура для идентификации конкретного платежа."""
    provider: PaymentProvider
    payment_provider_id: str
    payment_action: enums.PaymentAction
    sub_token: str

# ===== Главное меню =====
async def show_main(callback_query: types.CallbackQuery):
    use_case = GetMainMenuUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    if not dto.agreed_to_policy:
        await callback_query.message.edit_text(
            texts.txt_agreement(),
            reply_markup=keyboards.kb_agreement(),
            disable_web_page_preview=True
        )

    else:
        await callback_query.message.edit_text(
            texts.txt_main(dto.sub_end_at, dto.is_sub_active),
            reply_markup=keyboards.kb_main(not dto.trial_used, dto.is_sub_active, dto.sub_id)
        )

# Тарифы, покупка
async def show_plans(callback_query: types.CallbackQuery, callback_data: callbacks.PlansCallback):
    use_case = GetAvailablePlansUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_plans(dto.plans),
        reply_markup=keyboards.kb_plans(
            action=callback_data.action,
            plans=dto.plans,
            pending_payment_id=dto.pending_payment_id,
            sub_id=callback_data.sub_id
        )
    )

async def show_purchase_pending(callback_query: types.CallbackQuery, callback_data: callbacks.PurchasePendingCallback):
    use_case = CreatePaymentUseCase(build_uow(), await get_platega_client())
    result = await use_case.execute(
        tg_id=callback_query.from_user.id,
        username=callback_query.from_user.username,
        payment_action=callback_data.action,
        currency=config.CURRENCY,
        provider=enums.PaymentProvider.PLATEGA, # Заглушка
        plan_id=callback_data.plan_id,
        payment_method=enums.PaymentMethod.SBPQR,
        sub_id=callback_data.sub_id,
        tg_chat_id=callback_query.message.chat.id,
        tg_message_id=callback_query.message.message_id
    )

    if result.success:
        await callback_query.message.edit_text(
            texts.txt_purchase_pending(result.plan_name, result.price),
            reply_markup=keyboards.kb_purchase_pending(payment_link=result.payment_link)
        )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

async def show_purchase_success(callback_query: types.CallbackQuery, callback_data: PurchaseSuccessData):
    if callback_data.payment_action is enums.PaymentAction.CREATE:
        await callback_query.message.edit_text(
            texts.txt_purchase_success(callback_data.sub_token),
            reply_markup=keyboards.kb_purchase_success(callback_data.sub_token)
        )

    elif callback_data.payment_action is enums.PaymentAction.RENEW:
        await callback_query.message.edit_text(
            texts.txt_renew_success(),
            reply_markup=keyboards.kb_renew_success()
        )

    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

# Пробный период
async def show_trial(callback_query: types.CallbackQuery):
    use_case = ActivateTrialUseCase(build_uow(), get_vpn_gateway_factory())
    result = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    if result.success:
        if result.action is enums.PaymentAction.CREATE:
            await callback_query.message.edit_text(
                texts.txt_trial_created(result.sub_end_at, result.sub_token),
                reply_markup=keyboards.kb_trial(result.sub_token)
            )
        else:
            await callback_query.message.edit_text(
                texts.txt_trial_renewed(result.sub_end_at, result.sub_token),
                reply_markup=keyboards.kb_trial(result.sub_token)
            )

    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

# Мои ключи
async def show_my_sub(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_my_sub(dto.sub_end_at, dto.is_sub_active, dto.sub_token),
        reply_markup=keyboards.kb_my_sub(dto.sub_token, dto.sub_id)
    )

# ===== Инструкции =====
async def show_instruction(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_instruction(), reply_markup=keyboards.kb_instruction())

# Телефон
async def show_phone(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_phone(), reply_markup=keyboards.kb_phone())
# Iphone
async def show_iphone(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.IPHONE, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.IPHONE)
    )
async def show_problem_iphone(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.IPHONE, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.IPHONE)
    )
# Android
async def show_android(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.ANDROID, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.ANDROID)
    )
async def show_problem_android(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.ANDROID, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.ANDROID)
    )
# Huawei
async def show_huawei(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.HUAWEI, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.HUAWEI)
    )
async def show_problem_huawei(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.HUAWEI, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.HUAWEI)
    )

# ПК
async def show_computer(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.COMPUTER, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.COMPUTER)
    )
async def show_problem_computer(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.COMPUTER, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.COMPUTER)
    )

# Телевизор
async def show_tv(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_tv(), reply_markup=keyboards.kb_tv())
# Apple TV
async def show_apple_tv(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.APPLE_TV, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.APPLE_TV)
    )
async def show_problem_apple_tv(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.APPLE_TV, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.APPLE_TV)
    )
# Android TV
async def show_android_tv(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_happ_setup(Platform.ANDROID_TV, dto.sub_token),
        reply_markup=keyboards.kb_happ_setup(Platform.ANDROID_TV)
    )
async def show_problem_android_tv(callback_query: types.CallbackQuery):
    use_case = GetUserSubUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_v2raytun_setup(Platform.ANDROID_TV, dto.sub_token),
        reply_markup=keyboards.kb_v2raytun_setup(Platform.ANDROID_TV)
    )


ScreenHandler = Callable[..., Awaitable[None]]
screens: dict[Screen, ScreenHandler] = {
    # ===== Главное меню =====
    Screen.MAIN: show_main,

    # Тарифы, покупка
    Screen.PLANS: show_plans,
    Screen.PURCHASE_PENDING: show_purchase_pending,
    Screen.PURCHASE_SUCCESS: show_purchase_success,

    # Пробный период
    Screen.TRIAL: show_trial,

    # Мои ключи
    Screen.MY_SUB: show_my_sub,

# ===== Инструкции =====
    Screen.INSTRUCTION: show_instruction,

    # Телефон
    Screen.PHONE: show_phone,
    # Iphone
    Screen.IPHONE: show_iphone,
    Screen.PROBLEM_IPHONE: show_problem_iphone,
    # Android
    Screen.ANDROID: show_android,
    Screen.PROBLEM_ANDROID: show_problem_android,
    # Huawei
    Screen.HUAWEI: show_huawei,
    Screen.PROBLEM_HUAWEI: show_problem_huawei,

    # ПК
    Screen.COMPUTER: show_computer,
    Screen.PROBLEM_COMPUTER: show_problem_computer,

    # Телевизор
    Screen.TV: show_tv,
    # Apple TV
    Screen.APPLE_TV: show_apple_tv,
    Screen.PROBLEM_APPLE_TV: show_problem_apple_tv,
    # Android TV
    Screen.ANDROID_TV: show_android_tv,
    Screen.PROBLEM_ANDROID_TV: show_problem_android_tv
}