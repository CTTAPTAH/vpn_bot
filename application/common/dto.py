"""
DTO (Data Transfer Objects), используемые для передачи данных
между backend-сервисами и слоями отображения (screens).

В этом файле хранятся общие dto, которые нужны dto
для определённых use_cases.

Каждый DTO описывает данные, необходимые для формирования
конкретного пользовательского экрана.
"""
from dataclasses import dataclass

@dataclass
class PlanDTO:
    """Информация о тарифе."""
    id: int
    name: str
    price: int
    duration_months: int