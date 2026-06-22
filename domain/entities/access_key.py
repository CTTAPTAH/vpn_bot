from dataclasses import dataclass
@dataclass
class AccessKey:
    """Доменная модель ключа доступа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    server_id: int
    sub_id: int
    vless_link: str
    id: int | None = None