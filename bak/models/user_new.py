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


class PatientProfile(BaseModel):
    """Enhanced patient profile with better validation and relationships"""
    __tablename__ = 'patient_profiles'
    
    # One-to-one relationship with User
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, unique=True)
    
    # Demographics
    age: Mapped[Optional[int]] = mapped_column()
    gender: Mapped[Optional[str]] = mapped_column(String(20))  # Could be FK to Gender table
    date_of_birth: Mapped[Optional[datetime]] = mapped_column()
    
    # Education and background
    educational_level: Mapped[Optional[str]] = mapped_column(String(50))
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    cultural_background: Mapped[Optional[str]] = mapped_column(String(100))
    languages_spoken: Mapped[Optional[str]] = mapped_column(String(200))  # JSON array
    
    # Medical information
    medical_conditions: Mapped[Optional[str]] = mapped_column(Text)
    medications: Mapped[Optional[str]] = mapped_column(Text)
    medical_history: Mapped[Optional[str]] = mapped_column(Text)
    
    # Emergency contact
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    emergency_contact_relationship: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Consent and preferences
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    research_participation_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_language: Mapped[str] = mapped_column(String(5), default='id')
    
    # Profile completion tracking
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_percentage: Mapped[int] = mapped_column(default=0)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="patient_profile")
    
    def calculate_completion_percentage(self) -> int:
        """Calculate profile completion percentage"""
        total_fields = 15  # Adjust based on required fields
        completed_fields = 0
        
        if self.age: completed_fields += 1
        if self.gender: completed_fields += 1
        if self.educational_level: completed_fields += 1
        if self.occupation: completed_fields += 1
        if self.cultural_background: completed_fields += 1
        if self.emergency_contact_name: completed_fields += 1
        if self.emergency_contact_phone: completed_fields += 1
        # Add more field checks as needed
        
        percentage = int((completed_fields / total_fields) * 100)
        self.completion_percentage = percentage
        self.profile_completed = percentage >= 80
        
        return percentage
    
    def __repr__(self) -> str:
        return f"<PatientProfile for User {self.user.username if self.user else self.user_id}>"