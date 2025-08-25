"""
Modern User Model - Clean implementation with proper relationships
Replaces the old User model with better design and SQLAlchemy 2.0 patterns
"""
from typing import Optional, List
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, StatusMixin


class User(BaseModel, UserMixin, StatusMixin):
    """User model with proper FK relationships and modern SQLAlchemy 2.0 syntax"""
    __tablename__ = 'users'
    
    # Basic user fields
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Foreign key to UserType table (no more hardcoded strings!)
    user_type_id: Mapped[int] = mapped_column(ForeignKey('user_type.id'), nullable=False)
    
    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Account status
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column()
    login_count: Mapped[int] = mapped_column(default=0)
    
    # Relationships with proper typing
    user_type: Mapped["UserType"] = relationship(back_populates="users")
    patient_profile: Mapped[Optional["PatientProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    assessments: Mapped[List["Assessment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    
    def set_password(self, password: str) -> None:
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    def is_patient(self) -> bool:
        """Check if user is a patient"""
        return self.user_type.name == 'patient'
    
    def is_admin(self) -> bool:
        """Check if user is an admin"""
        return self.user_type.name in ('admin', 'superuser')

    def is_superuser(self) -> bool:
        """Check if user is a superuser"""
        return self.user_type.name == 'superuser'
    
    def record_login(self) -> None:
        """Record successful login"""
        self.last_login = datetime.utcnow()
        self.login_count += 1

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.user_type.name if self.user_type else 'No Type'})>"