"""
Базовый класс для всех ORM-моделей проекта.

Все таблицы наследуются от Base.
SQLAlchemy и Alembic используют его,
чтобы обнаружить и управлять схемой БД.
"""
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass
