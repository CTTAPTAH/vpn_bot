"""
DTO (Data Transfer Objects), используемые для передачи данных
между backend-сервисами и слоями отображения (screens).

В этом файле хранятся общие dto, которые нужны dto
для определённых use_cases.

Каждый DTO описывает данные, необходимые для формирования
конкретного пользовательского экрана.
"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class KeyDTO:
    """Информация о ключе пользователя. Лучше модели, так как есть название тарифа, а не его id."""
    id: int
    plan_name: str
    end_at: datetime
    is_expired: bool