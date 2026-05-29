from datetime import datetime

import presentation.telegram.texts.branding as branding
from application.use_cases.get_user_tickets import TicketPreview
from application.use_cases.get_ticket_messages import MessagePreview
from domain.enums import TicketStatus, MessageSenderType

def txt_main() -> str:
    return f"""👋 Добро пожаловать в поддержку <b>{branding.VPN_NAME}</b>!

Если у вас есть вопросы или проблемы, нажмите <b>«НАПИСАТЬ ЗАПРОС»</b> и опишите ситуацию.

Наша поддержка всегда на связи и готова помочь."""

def txt_faq() -> str:
    return """❓ <b>Часто задаваемые вопросы (FAQ)</b>

<blockquote><b>Можно ли использовать подключение на нескольких устройствах одновременно?</b></blockquote>
- Да, один ключ можно использовать на нескольких устройствах, но одновременно подключены могут быть только 5 устройств.

<blockquote><b>Почему у вас такой маленький выбор серверов?</b></blockquote>
- Наши алгоритмы подбирают самые быстрые и надёжные серверы, поэтому их не так много.

<blockquote><b>Подключение бывает нестабильным?</b></blockquote>
- Качество соединения может зависеть от особенностей сети и загруженности каналов,
поэтому иногда оно становится менее стабильным.

<blockquote><b>Как отменить подписку?</b></blockquote>
- Зайдите в: «🔑 Мои ключи», выберите "активную подписку" и нажмите «Отменить подписку».

<blockquote><b>Что делать, если ключ не работает?</b></blockquote>
- Проверьте, что ключ скопирован полностью
- Убедитесь, что ключ выбран в приложении
- При необходимости переустановите приложение и импортируйте ключ заново

<blockquote><b>Поддерживаются ли Smart TV или консоли?</b></blockquote>
Поддержка зависит от платформы.
- Android TV - поддерживается.
- Apple TV - поддерживается через Shadowrocket.
- LG и Samsung Smart TV — не поддерживаются."""

def txt_write_request() -> str:
    return f"""💬 <b>Опишите проблему</b>

Напишите, с чем столкнулись, и наша поддержка свяжется с вами в ближайшее время."""

def txt_my_requests(tickets: list[TicketPreview]) -> str:
    if not tickets:
        return "📩 <b>Ваши обращения</b>\n\nУ вас пока нет обращений."

    return """📩 <b>Ваши обращения</b>

🟢 – открытое
⚫️ – закрытое

Следите за статусом своих запросов и получайте ответы от поддержки."""

def txt_ticket_history(created_at: datetime, status: TicketStatus, messages: list[MessagePreview]) -> str:
    status = "открыт" if status is TicketStatus.OPEN else "закрыт"
    formatted_date = created_at.strftime("%d.%m.%Y %H:%M")
    text = f"📩 Обращение от {formatted_date}\nСтатус: {status}\n\n"

    for message in messages:
        if message.sender is MessageSenderType.USER:
            text += "👤 Вы:\n"
        else:
            text += "💬 Поддержка:\n"

        text += f"{message.message}\n\n"

    return text