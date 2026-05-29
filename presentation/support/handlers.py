from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import app.container as container
from application.use_cases.admin_reply_to_ticket import AdminReplyToTicket
from application.use_cases.create_or_append_user_ticket_message import CreateOrAppendUserTicketMessage
from application.use_cases.get_open_ticket_thread_id import GetOpenTicketThreadId
from application.use_cases.close_ticket import CloseTicket
from application.use_cases.get_user_tickets import GetUserTickets
from application.use_cases.get_ticket_messages import GetTicketMessages
from presentation.support.bot import bot
from presentation.support.states import SupportStates
import presentation.support.texts as texts
import presentation.support.keyboards as keyboards
import presentation.support.callbacks as callbacks
import core.config as config

def register_handlers():
    router = Router()
    @router.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        await state.set_state(SupportStates.main)
        await message.answer(texts.txt_main(), reply_markup=keyboards.kb_main())
        await message.delete()

    @router.callback_query(F.data == "faq")
    async def process_faq(callback_query: types.CallbackQuery, state: FSMContext):
        await state.set_state(SupportStates.faq)
        await callback_query.answer()
        await callback_query.message.edit_text(texts.txt_faq(), reply_markup=keyboards.kb_faq())

    @router.callback_query(F.data == "my_request")
    async def process_my_request(callback_query: types.CallbackQuery, state: FSMContext):
        await state.set_state(SupportStates.my_request)
        use_case = GetUserTickets(container.build_uow())
        dto = await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)

        await callback_query.answer()
        await callback_query.message.edit_text(
            texts.txt_my_requests(dto.tickets),
            reply_markup=keyboards.kb_my_requests(dto.tickets)
        )

    @router.callback_query(F.data == "write_request")
    async def process_write_request(callback_query: types.CallbackQuery, state: FSMContext):
        await state.set_state(SupportStates.writing)
        await callback_query.answer()
        await callback_query.message.edit_text(texts.txt_write_request(), reply_markup=keyboards.kb_write_request())

    @router.callback_query(F.data == "back")
    async def process_back(callback_query: types.CallbackQuery, state: FSMContext):
        await state.set_state(SupportStates.main)
        await callback_query.answer()
        await callback_query.message.edit_text(texts.txt_main(), reply_markup=keyboards.kb_main())

    # Восстановление истории переписки в выбранном обращении
    @router.callback_query(callbacks.TicketCallback.filter())
    async def handle_ticket_history(callback_query: types.CallbackQuery, callback_data: callbacks.TicketCallback):
        use_case = GetTicketMessages(container.build_uow())
        result = await use_case.execute(callback_data.ticket_id)

        await callback_query.answer()
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=texts.txt_ticket_history(result.created_at, result.status, result.messages)
        )

    # Закрытие обращения и удаление топика
    @router.message(Command("close"), F.chat.id == config.SUPPORT_GROUP_ID)
    async def handle_close_ticket(message: types.Message):
        # Закрываем тикет
        use_case = CloseTicket(container.build_uow())
        dto = await use_case.execute(message.message_thread_id)

        if not dto.success:
            await message.reply("Ошибка: обращение не найдено.")
            return

        # Отправляем сообщение пользователю о закрытии тикета
        await bot.send_message(
            chat_id=dto.tg_id,
            text="✅ Обращение закрыто.\n\nЕсли проблема появится снова — вы можете создать новое обращение."
        )

        # Удалить топик
        await bot.delete_forum_topic(
            chat_id=config.SUPPORT_GROUP_ID,
            message_thread_id=message.message_thread_id
        )

    # Принимаем текст только в состоянии writing
    @router.message(SupportStates.writing)
    async def handle_user_message(message: types.Message):
        if not message.text:
            await message.answer("Поддерживаются только текстовые сообщения")
            return

        await message.answer("Сообщение отправлено! Ожидайте ответа.")

        # Создать топик или получит существующий
        use_case_get_thread = GetOpenTicketThreadId(container.build_uow())
        thread_id = await use_case_get_thread.execute(
            tg_id=message.from_user.id,
            username=message.from_user.username
        )

        if thread_id is None:
            topic = await bot.create_forum_topic(
                chat_id=config.SUPPORT_GROUP_ID,
                name=f"@{message.from_user.username} - {message.text[:20]}"
            )
            thread_id = topic.message_thread_id

        # Отправить сообщение в топик
        username = message.from_user.username or "без username"
        await bot.send_message(
            chat_id=config.SUPPORT_GROUP_ID,
            message_thread_id=thread_id,
            text=(
                f"📩 Новое обращение\n"
                f"👤 Username: @{username}\n"
                f"🆔 TG ID: <code>{message.from_user.id}</code>\n\n"
                f"{message.text}"
            )
        )

        # Сохранить в БД
        use_case = CreateOrAppendUserTicketMessage(container.build_uow())
        await use_case.execute(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            text=message.text,
            thread_id=thread_id
        )

    # Ответ админа в группе
    @router.message(F.chat.id == config.SUPPORT_GROUP_ID, F.from_user.is_bot == False)
    async def handle_admin_reply(message: types.Message):
        if not message.message_thread_id:
            return

        use_case = AdminReplyToTicket(container.build_uow())
        dto = await use_case.execute(
            thread_id=message.message_thread_id,
            text=message.text
        )

        if dto.success:
            await bot.send_message(
                chat_id=dto.tg_id,
                text=f"💬 Ответ поддержки:\n\n{message.text}"
            )
            await message.reply("Сообщение отправлено!")
        else:
            await message.reply("Ошибка: не удалось найти пользователя.")

    return router