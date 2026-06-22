from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class AccessKey(Base):
    """
    ORM-модель ключа доступа.

    Описывает таблицу `access_keys` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "access_keys"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    sub_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="id подписки, в которую входит ключ."
    )

    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="id сервера, на котором расположен ключ."
    )

    vless_link: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="vless ссылка ключа. Важен как кэш, чтобы уменьшить количество запросов к xui."
    )