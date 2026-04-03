"""
Функции отображения экранов бота.

Экранные функции (show_xxx) – отвечают за отображение текста и клавиатур.
Используются в process_back() и при переключении между разделами.
"""
from aiogram import types
from typing import Callable, Awaitable

from app.container import get_vpn_gateway_factory, build_uow
from application.use_cases.get_main_menu import GetMainMenuUseCase
from application.use_cases.get_available_plans import GetAvailablePlansUseCase
from application.use_cases.create_payment import CreatePaymentUseCase
from application.use_cases.confirm_payment import ConfirmPaymentUseCase
from application.use_cases.activate_trial import (ActiveTrialUseCase, ActiveTrialError,
                                                  ActiveTrialSuccess, ActiveTrialChooseKey)
from application.use_cases.extend_trial import ExtendTrialUseCase
from application.use_cases.user_keys import GetUserKeysUseCase
from application.use_cases.selected_key import GetSelectedKeyUseCase
from application.use_cases.get_key_for_deletion import GetKeyForDeletionUseCase
from application.services.server_selection import ServerSelectionService
from presentation.telegram.states.states import Screen
import presentation.telegram.texts.texts as texts
import presentation.telegram.keyboards.keyboards as keyboards
import presentation.telegram.callbacks.callbacks as callbacks
import domain.enums as enums

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
            texts.txt_main(dto.active_keys),
            reply_markup=keyboards.kb_main(not dto.trial_used)
        )

async def show_view_agreement(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_view_agreement(),
        reply_markup=keyboards.kb_view_agreement(),
        disable_web_page_preview=True
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
            key_id=callback_data.key_id
        )
    )

async def show_purchase_pending(callback_query: types.CallbackQuery, callback_data: callbacks.PurchasePendingCallback):
    use_case = CreatePaymentUseCase(build_uow())
    result = await use_case.execute(
        tg_id=callback_query.from_user.id,
        username=callback_query.from_user.username,
        payment_action=callback_data.action,
        provider=enums.PaymentProvider.YOUMONEY, # Заглушка
        plan_id=callback_data.plan_id
    )

    if result.success:
        if result.is_existing:
            await callback_query.message.edit_text(
                texts.txt_existing_payment(result.plan_name, result.price),
                reply_markup=keyboards.kb_purchase_pending(
                    payment_link=result.payment_link,
                    action=callback_data.action,
                    payment_id=result.payment_id,
                    key_id=callback_data.key_id
                )
            )
        else:
            await callback_query.message.edit_text(
                texts.txt_purchase_pending(result.plan_name, result.price),
                reply_markup=keyboards.kb_purchase_pending(
                    payment_link=result.payment_link,
                    action=callback_data.action,
                    payment_id=result.payment_id,
                    key_id=callback_data.key_id
                )
            )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

async def show_purchase_success(callback_query: types.CallbackQuery, callback_data: callbacks.PurchaseSuccessCallback):
    use_case = ConfirmPaymentUseCase(build_uow(), get_vpn_gateway_factory(), ServerSelectionService())
    result = await use_case.execute(
        tg_id=callback_query.from_user.id,
        username=callback_query.from_user.username,
        payment_id=callback_data.payment_id,
        key_id=callback_data.key_id
    )

    if result.success:
        await callback_query.message.edit_text(
            texts.txt_purchase_success(),
            reply_markup=keyboards.kb_purchase_success()
        )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )


# Пробный период
async def show_trial(callback_query: types.CallbackQuery):
    use_case = ActiveTrialUseCase(build_uow(), get_vpn_gateway_factory(), ServerSelectionService())
    result = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    if isinstance(result, ActiveTrialError):
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )
    elif isinstance(result, ActiveTrialSuccess):
        await callback_query.message.edit_text(
            texts.txt_trial(result.num_days, result.vless_link),
            reply_markup=keyboards.kb_trial()
        )
    elif isinstance(result, ActiveTrialChooseKey):
        await callback_query.message.edit_text(
            texts.txt_trial_limit_reached(result.count_keys),
            reply_markup=keyboards.kb_trial_limit(result.keys)
        )

async def show_extend_trial(callback_query: types.CallbackQuery, callback_data: callbacks.ExtendTrialCallback):
    use_case = ExtendTrialUseCase(build_uow(), get_vpn_gateway_factory())
    result = await use_case.execute(
        tg_id=callback_query.from_user.id,
        username=callback_query.from_user.username,
        key_id=callback_data.key_id
    )

    if result.success:
        await callback_query.message.edit_text(
            texts.txt_extend_trial(result.plan_name, result.num_days),
            reply_markup=keyboards.kb_extend_trial()
        )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

# Мои ключи
async def show_my_keys(callback_query: types.CallbackQuery):
    use_case = GetUserKeysUseCase(build_uow())
    dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

    await callback_query.message.edit_text(
        texts.txt_my_keys(dto.count_all_keys, dto.count_active_keys, dto.keys),
        reply_markup=keyboards.kb_my_keys(dto.keys)
    )

async def show_selected_key(callback_query: types.CallbackQuery, callback_data: callbacks.SelectedKeyCallback):
    use_case = GetSelectedKeyUseCase(build_uow())
    result = await use_case.execute(callback_data.key_id, callback_query.from_user.id)

    if result.success:
        await callback_query.message.edit_text(
            texts.txt_selected_key(result.key, result.vless),
            reply_markup=keyboards.kb_selected_key(result.key.id)
        )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

async def show_confirm_delete_key(callback_query: types.CallbackQuery,
                                  callback_data: callbacks.ConfirmDeleteKeyCallback):
    use_case = GetKeyForDeletionUseCase(build_uow())
    result = await use_case.execute(callback_data.key_id, callback_query.from_user.id)

    if result.success:
        await callback_query.message.edit_text(
            texts.txt_confirm_delete_key(result.key),
            reply_markup=keyboards.kb_confirm_delete_key(result.key.id)
        )
    else:
        await callback_query.message.edit_text(
            texts.txt_unknown_error(),
            reply_markup=keyboards.kb_error()
        )

# Поддержка
async def show_help(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_help(), reply_markup=keyboards.kb_help())

async def show_faq(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_faq(), reply_markup=keyboards.kb_faq())

async def show_request_help(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_request_help(), reply_markup=keyboards.kb_request_help())

async def show_my_requests(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_my_requests(), reply_markup=keyboards.kb_my_requests())

# ===== Инструкции =====
async def show_instruction(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_instruction(), reply_markup=keyboards.kb_instruction())

# APPLE
async def show_apple(callback_query: types.CallbackQuery):
    vless = "vless"
    await callback_query.message.edit_text(texts.txt_apple(), reply_markup=keyboards.kb_apple(vless))

async def show_problems_apple(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_problems_apple(), reply_markup=keyboards.kb_problems_apple())

async def show_no_connection_apple(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_no_connection_apple(),
        reply_markup=keyboards.kb_no_connection_apple()
    )

async def show_second_method_apple(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_second_method_apple(),
        reply_markup=keyboards.kb_second_method_apple()
    )

# ANDROID
async def show_android(callback_query: types.CallbackQuery):
    vless = "vless"
    await callback_query.message.edit_text(texts.txt_android(), reply_markup=keyboards.kb_android(vless))

async def show_problems_android(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_problems_android(), reply_markup=keyboards.kb_problems_android())

async def show_no_connection_android(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_no_connection_android(),
        reply_markup=keyboards.kb_no_connection_android()
    )

async def show_second_method_android(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_second_method_android(),
        reply_markup=keyboards.kb_second_method_android()
    )

# WINDOWS
async def show_windows(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_windows(),
        reply_markup=keyboards.kb_windows(),
        disable_web_page_preview=True
    )

async def show_pc_apps(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_pc_apps(), reply_markup=keyboards.kb_pc_apps())

# TV
async def show_tv(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_tv(), reply_markup=keyboards.kb_tv())

async def show_android_tv(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_android_tv(), reply_markup=keyboards.kb_android_tv())

async def show_apple_tv(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_apple_tv(), reply_markup=keyboards.kb_apple_tv())

# HUAWEI
async def show_huawei(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(texts.txt_huawei(), reply_markup=keyboards.kb_huawei())

async def show_second_method_huawei(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        texts.txt_second_method_huawei(),
        reply_markup=keyboards.kb_second_method_huawei()
    )

ScreenHandler = Callable[..., Awaitable[None]]
screens: dict[Screen, ScreenHandler] = {
    # ===== Главное меню =====
    Screen.MAIN: show_main,
    Screen.VIEW_AGREEMENT: show_view_agreement,

    # Тарифы, покупка
    Screen.PLANS: show_plans,
    Screen.PURCHASE_PENDING: show_purchase_pending,
    Screen.PURCHASE_SUCCESS: show_purchase_success,

    # Пробный период
    Screen.TRIAL: show_trial,
    Screen.EXTEND_TRIAL: show_extend_trial,

    # Мои ключи
    Screen.MY_KEYS: show_my_keys,
    Screen.SELECTED_KEY: show_selected_key,
    Screen.CONFIRM_DELETE_KEY: show_confirm_delete_key,

    # Поддержка
    Screen.HELP: show_help,
    Screen.FAQ: show_faq,
    Screen.REQUEST_HELP: show_request_help,
    Screen.MY_REQUESTS: show_my_requests,

    # ===== Инструкции =====
    Screen.INSTRUCTION: show_instruction,

    # APPLE
    Screen.APPLE: show_apple,
    Screen.PROBLEMS_APPLE: show_problems_apple,
    Screen.NO_CONNECTION_APPLE: show_no_connection_apple,
    Screen.SECOND_METHOD_APPLE: show_second_method_apple,

    # ANDROID
    Screen.ANDROID: show_android,
    Screen.PROBLEMS_ANDROID: show_problems_android,
    Screen.NO_CONNECTION_ANDROID: show_no_connection_android,
    Screen.SECOND_METHOD_ANDROID: show_second_method_android,

    # WINDOWS
    Screen.WINDOWS: show_windows,
    Screen.PC_APPS: show_pc_apps,

    # TV
    Screen.TV: show_tv,
    Screen.ANDROID_TV: show_android_tv,
    Screen.APPLE_TV: show_apple_tv,

    # HUAWEI
    Screen.HUAWEI: show_huawei,
    Screen.SECOND_METHOD_HUAWEI: show_second_method_huawei,
}