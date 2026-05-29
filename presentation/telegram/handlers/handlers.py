"""
Основные обработчики Telegram-бота.

Этот модуль регистрирует handlers и связывает их
с зависимостями приложения (например VPN gateway).
"""
from aiogram import Router, types, F
from aiogram.filters import Command

from application.use_cases.get_main_menu import GetMainMenuUseCase
from presentation.telegram.navigation.navigation import go_to, go_back, go_back_to
from presentation.telegram.states.states import Screen
from presentation.telegram.enums import Action
from presentation.telegram.states.manager import state_manager
import presentation.telegram.callbacks.callbacks as callbacks
import presentation.telegram.texts.texts as texts
import presentation.telegram.keyboards.keyboards as keyboards
import presentation.telegram.actions.actions as actions
import app.container as container
from presentation.telegram.bot import bot

def register_handlers():
   """Создаёт и настраивает Router с обработчиками."""
   router = Router()

   # Команда start
   @router.message(Command("start"))
   async def cmd_start(message: types.Message):
      await bot.set_my_description(description="")
      use_case = GetMainMenuUseCase(container.build_uow())
      dto = await use_case.execute(message.from_user.id, message.from_user.username)

      if not dto.agreed_to_policy:
         await message.answer(
            texts.txt_agreement(),
            reply_markup=keyboards.kb_agreement(),
            disable_web_page_preview=True
         )

      else:
         await message.answer(
            texts.txt_main(dto.active_keys),
            reply_markup=keyboards.kb_main(not dto.trial_used)
         )
         state_manager.reset_state(message.from_user.id)
         state_manager.push_state(message.from_user.id, Screen.MAIN)
      await message.delete()

   # Команда docs
   @router.message(Command("docs"))
   async def cmd_docs(message: types.Message):
      await message.answer(texts.txt_view_agreement(), disable_web_page_preview=True)
      await message.delete()

   # Кнопка назад
   @router.callback_query(F.data == Action.BACK)
   async def process_back(callback_query: types.CallbackQuery):
      await go_back(callback_query)

   @router.callback_query(F.data == Action.GO_BACK_TO_MENU)
   async def process_go_back_to_menu(callback_query: types.CallbackQuery):
      await go_back_to(callback_query, Screen.MAIN)

   # ===== Главное меню =====
   @router.callback_query(F.data == Screen.MAIN)
   async def process_main(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.MAIN, reset=True)

   @router.callback_query(F.data == Action.AGREE)
   async def process_agree(callback_query: types.CallbackQuery):
      await actions.agreement_with_policy(callback_query)
      await go_to(callback_query, Screen.MAIN)

   # Тарифы, покупка
   @router.callback_query(callbacks.PlansCallback.filter())
   async def process_plans(callback_query: types.CallbackQuery, callback_data: callbacks.PlansCallback):
      await go_to(callback_query, Screen.PLANS, data=callback_data)

   @router.callback_query(callbacks.PurchasePendingCallback.filter())
   async def process_purchase_pending(callback_query: types.CallbackQuery,
                                      callback_data: callbacks.PurchasePendingCallback):
      await go_to(callback_query, Screen.PURCHASE_PENDING, data=callback_data)

   @router.callback_query(callbacks.PurchaseSuccessCallback.filter())
   async def process_purchase_success(callback_query: types.CallbackQuery,
                                      callback_data: callbacks.PurchaseSuccessCallback):
      await go_to(callback_query, Screen.PURCHASE_SUCCESS, data=callback_data)

   # Пробный период
   @router.callback_query(F.data == Screen.TRIAL)
   async def process_active_trial(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.TRIAL)

   @router.callback_query(callbacks.ExtendTrialCallback.filter())
   async def process_extend_trial(callback_query: types.CallbackQuery, callback_data: callbacks.ExtendTrialCallback):
      await go_to(callback_query, Screen.EXTEND_TRIAL, data=callback_data)

   # Мои ключи
   @router.callback_query(F.data == Screen.MY_KEYS)
   async def process_my_keys(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.MY_KEYS)

   @router.callback_query(callbacks.SelectedKeyCallback.filter())
   async def process_selected_key(callback_query: types.CallbackQuery, callback_data: callbacks.SelectedKeyCallback):
      await go_to(callback_query, Screen.SELECTED_KEY, data=callback_data)

   @router.callback_query(callbacks.DeleteKeyCallback.filter())
   async def process_key_deleted(callback_query: types.CallbackQuery, callback_data: callbacks.DeleteKeyCallback):
      answer = await actions.delete_key(callback_query, callback_data)
      await go_back_to(callback_query, Screen.MY_KEYS, answer=answer)

   # ===== Инструкции =====
   @router.callback_query(F.data == Screen.INSTRUCTION)
   async def process_instruction(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.INSTRUCTION)

   # 2.1. Инструкция - Apple
   @router.callback_query(F.data == Screen.APPLE)
   async def process_apple(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.APPLE)
   # 2.1.1. Инструкция - Apple - Проблемы
   @router.callback_query(F.data == Screen.PROBLEMS_APPLE)
   async def process_problems_apple(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.PROBLEMS_APPLE)
   # 2.1.1.1 Инструкция - Apple - Проблемы - Подключения нет
   @router.callback_query(F.data == Screen.NO_CONNECTION_APPLE)
   async def process_no_connection_apple(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.NO_CONNECTION_APPLE)
   # 2.1.2. Инструкция - Apple - 2 способ
   @router.callback_query(F.data == Screen.SECOND_METHOD_APPLE)
   async def process_second_method_apple(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.SECOND_METHOD_APPLE)

   # 2.2. Инструкция - Android
   @router.callback_query(F.data == Screen.ANDROID)
   async def process_android(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.ANDROID)
   # 2.2.1. Инструкция - Android - Проблемы
   @router.callback_query(F.data == Screen.PROBLEMS_ANDROID)
   async def process_problems_android(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.PROBLEMS_ANDROID)
   # 2.2.1.1 Инструкция - Android - Проблемы - Подключения нет
   @router.callback_query(F.data == Screen.NO_CONNECTION_ANDROID)
   async def process_no_connection_android(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.NO_CONNECTION_ANDROID)
   # 2.2.2. Инструкция - Android - 2 способ
   @router.callback_query(F.data == Screen.SECOND_METHOD_ANDROID)
   async def process_second_method_android(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.SECOND_METHOD_ANDROID)

   # 2.3. Инструкция - Windows
   @router.callback_query(F.data == Screen.WINDOWS)
   async def process_windows(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.WINDOWS)
   # 2.3.1. Инструкция - Windows - избранные приложения
   @router.callback_query(F.data == Screen.PC_APPS)
   async def process_pc_apps(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.PC_APPS)

   # 2.4. Инструкция - TV
   @router.callback_query(F.data == Screen.TV)
   async def process_tv(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.TV)
   # 2.4.1. Инструкция - Android TV
   @router.callback_query(F.data == Screen.ANDROID_TV)
   async def process_android_tv(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.ANDROID_TV)
   # 2.4.2. Инструкция - Apple TV
   @router.callback_query(F.data == Screen.APPLE_TV)
   async def process_apple_tv(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.APPLE_TV)

   # 2.5. Инструкция - Huawei
   @router.callback_query(F.data == Screen.HUAWEI)
   async def process_huawei(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.HUAWEI)
   # 2.5.2. Инструкция - Huawei - 2 способ
   @router.callback_query(F.data == Screen.SECOND_METHOD_HUAWEI)
   async def process_second_method_huawei(callback_query: types.CallbackQuery):
      await go_to(callback_query, Screen.SECOND_METHOD_HUAWEI)

   return router