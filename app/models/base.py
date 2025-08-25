"""
Modern SQLAlchemy 2.0 Base Classes
Provides DeclarativeBase and common mixins for clean ORM implementation
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Modern SQLAlchemy 2.0 DeclarativeBase"""
    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )


class IdMixin:
    """Mixin for primary key id column"""
    id: Mapped[int] = mapped_column(primary_key=True)


class BaseModel(Base, IdMixin, TimestampMixin):
    """Base model with id and timestamps"""
    __abstract__ = True


class NamedModel(BaseModel):
    """Base model for entities with name field"""
    __abstract__ = True
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"


class StatusMixin:
    """Mixin for entities with active/inactive status"""
    is_active: Mapped[bool] = mapped_column(default=True)