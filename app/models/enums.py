"""
Enum Tables - Replace hardcoded enums with proper database tables
All these were previously hardcoded strings or Python enums
"""
from typing import List, Optional

from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, NamedModel, StatusMixin


class AssessmentStatus(NamedModel, StatusMixin):
    """Status of an assessment (in_progress, completed, abandoned, etc.)"""
    __tablename__ = 'assessment_status'
    
    # Relationships
    assessments: Mapped[List["Assessment"]] = relationship(back_populates="status")


class UserType(NamedModel, StatusMixin):
    """User types (patient, admin, superuser)"""
    __tablename__ = 'user_type'
    
    # Permissions or other type-specific data
    permissions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="user_type")


class MediaType(NamedModel):
    """Media types (image, video) with their allowed extensions"""
    __tablename__ = 'media_type'
    
    # File extensions allowed for this media type
    extensions: Mapped[Optional[str]] = mapped_column(String(100))  # 'jpg,png,webp'
    mime_types: Mapped[Optional[str]] = mapped_column(String(200))  # 'image/jpeg,image/png'
    max_file_size_mb: Mapped[Optional[int]] = mapped_column(Integer, default=50)
    
    # Relationships
    emotion_data: Mapped[List["EmotionData"]] = relationship(back_populates="media_type")


class AssessmentType(NamedModel):
    """Types of assessments (phq9, open_questions)"""
    __tablename__ = 'assessment_type'
    
    # Configuration for this assessment type
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    default_order: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships
    emotion_data: Mapped[List["EmotionData"]] = relationship(back_populates="assessment_type")


class PHQ9Category(BaseModel):
    """PHQ-9 categories - formerly hardcoded PHQCategoryType enum"""
    __tablename__ = 'phq9_category'
    
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_question: Mapped[Optional[str]] = mapped_column(Text)
    
    # For internationalization
    name_en: Mapped[Optional[str]] = mapped_column(String(100))
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    default_question_en: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    phq9_responses: Mapped[List["PHQ9Response"]] = relationship(back_populates="category")
    
    def __repr__(self) -> str:
        return f"<PHQ9Category {self.number}: {self.name}>"


class ScaleLabel(BaseModel):
    """Dynamic scale labels - formerly hardcoded SCALE_LABEL_* values"""
    __tablename__ = 'scale_label'
    
    scale_value: Mapped[int] = mapped_column(Integer, nullable=False)
    label_text: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default='id')  # 'id', 'en'
    
    # Optional context for different assessment types
    context: Mapped[Optional[str]] = mapped_column(String(50))  # 'phq9', 'general'
    
    def __repr__(self) -> str:
        return f"<ScaleLabel {self.scale_value}: {self.label_text} ({self.language})>"


class SettingType(NamedModel):
    """Types of settings (recording, phq9, chat, etc.)"""
    __tablename__ = 'setting_type'
    
    # Data type validation
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'string', 'int', 'bool', 'float', 'json'
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # For choice-type settings
    choices: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of choices
    
    # Relationships
    assessment_settings: Mapped[List["AssessmentSetting"]] = relationship(back_populates="setting_type")
    
    def __repr__(self) -> str:
        return f"<SettingType {self.name} ({self.data_type})>"