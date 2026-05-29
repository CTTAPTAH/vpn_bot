from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from application.use_cases.get_user_tickets import TicketPreview
from domain.enums import TicketStatus
import presentation.support.callbacks as callbacks

# Часто используемы кнопки
BTN_BACK = InlineKeyboardButton(text="⬅️ Назад", callback_data="back")

# Поддержка
def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Часто задаваемые вопросы", callback_data="faq")],
        [InlineKeyboardButton(text="Написать запрос", callback_data="write_request")],
        [InlineKeyboardButton(text="Мои обращения", callback_data="my_request")]
    ])

def kb_faq() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_BACK]
    ])

def kb_write_request() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [BTN_BACK]
    ])

def kb_my_requests(tickets: list[TicketPreview]) -> InlineKeyboardMarkup:
    buttons = []

    for ticket in tickets:
        emoji = "🟢" if ticket.status == TicketStatus.OPEN else "⚫️"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {ticket.preview_text}",
            callback_data=callbacks.TicketCallback(ticket_id=ticket.ticket_id).pack()
        )])

    buttons.append([BTN_BACK])

    return InlineKeyboardMarkup(inline_keyboard=buttons)