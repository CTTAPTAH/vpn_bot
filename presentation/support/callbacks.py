from aiogram.filters.callback_data import CallbackData

class TicketCallback(CallbackData, prefix="ticket"):
    ticket_id: int