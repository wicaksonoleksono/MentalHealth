"""
Modern Settings System - NO MORE JSON COLUMNS!
Proper normalized settings with queryable, indexable data
"""
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class GlobalSetting(BaseModel):
    """Global application settings - replaces old AppSetting table"""
    __tablename__ = 'global_settings'
    
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(20), default='string')  # 'string', 'int', 'bool', 'float', 'json'
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))  # 'recording', 'phq9', 'chat', etc.
    
    def get_typed_value(self) -> Any:
        """Get value converted to proper type"""
        if not self.value:
            return None
        
        if self.data_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'int':
            try:
                return int(self.value)
            except ValueError:
                return None
        elif self.data_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return None
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return None
        else:  # string
            return self.value
    
    def set_typed_value(self, value: Any) -> None:
        """Set value from typed value"""
        if value is None:
            self.value = None
        elif isinstance(value, (dict, list)):
            import json
            self.value = json.dumps(value)
        elif isinstance(value, bool):
            self.value = str(value).lower()
        else:
            self.value = str(value)
    
    def __repr__(self) -> str:
        return f"<GlobalSetting {self.key}: {self.value}>"


class PHQ9Setting(BaseModel):
    """PHQ-9 specific settings per assessment - replaces JSON phq9_settings column"""
    __tablename__ = 'phq9_settings'
    
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    
    # PHQ-9 configuration settings
    randomize_questions: Mapped[bool] = mapped_column(Boolean, default=False)
    scale_min: Mapped[int] = mapped_column(Integer, default=0)
    scale_max: Mapped[int] = mapped_column(Integer, default=3)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Scale labels (could be FKs to ScaleLabel table)
    scale_labels: Mapped[Optional[str]] = mapped_column(Text)  # JSON temporarily, should be FK relations
    
    # Timing settings
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    show_progress: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship()
    
    def __repr__(self) -> str:
        return f"<PHQ9Setting for Assessment {self.assessment_id}>"


class RecordingSetting(BaseModel):
    """Recording settings per assessment - replaces JSON recording_settings column"""
    __tablename__ = 'recording_settings'
    
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    
    # Recording mode settings
    recording_mode: Mapped[str] = mapped_column(String(20), default='capture')  # 'capture', 'video'
    enable_recording: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Capture mode settings
    capture_mode: Mapped[str] = mapped_column(String(20), default='interval')  # 'interval', 'event_driven', 'video_continuous'
    capture_interval: Mapped[int] = mapped_column(Integer, default=5)  # seconds
    event_capture_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Event triggers
    capture_on_button_click: Mapped[bool] = mapped_column(Boolean, default=True)
    capture_on_message_send: Mapped[bool] = mapped_column(Boolean, default=True)
    capture_on_question_start: Mapped[bool] = mapped_column(Boolean, default=False)
    capture_on_typing_pause: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Media quality settings
    resolution: Mapped[str] = mapped_column(String(20), default='1280x720')
    image_quality: Mapped[float] = mapped_column(Float, default=0.8)
    video_quality: Mapped[str] = mapped_column(String(10), default='720p')
    video_format: Mapped[str] = mapped_column(String(10), default='webm')
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship()
    
    def __repr__(self) -> str:
        return f"<RecordingSetting for Assessment {self.assessment_id}>"


class ChatSetting(BaseModel):
    """Chat settings per assessment - replaces JSON chat_settings column"""
    __tablename__ = 'chat_settings'
    
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    
    # Chat behavior settings
    max_exchanges: Mapped[int] = mapped_column(Integer, default=10)
    max_response_length: Mapped[int] = mapped_column(Integer, default=500)
    enable_streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # AI model settings
    model_name: Mapped[Optional[str]] = mapped_column(String(50))
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=150)
    
    # Prompt settings
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship()
    
    def __repr__(self) -> str:
        return f"<ChatSetting for Assessment {self.assessment_id}>"


class UserPreference(BaseModel):
    """User-specific preferences and settings"""
    __tablename__ = 'user_preferences'
    
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    
    # Preference details
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_value: Mapped[Optional[str]] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(20), default='string')
    
    # Preference metadata
    category: Mapped[Optional[str]] = mapped_column(String(50))  # 'ui', 'notifications', 'privacy'
    description: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Relationships
    user: Mapped["User"] = relationship()
    
    def get_typed_value(self) -> Any:
        """Get preference value converted to proper type"""
        if not self.preference_value:
            return None
        
        if self.data_type == 'bool':
            return self.preference_value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'int':
            try:
                return int(self.preference_value)
            except ValueError:
                return None
        elif self.data_type == 'float':
            try:
                return float(self.preference_value)
            except ValueError:
                return None
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.preference_value)
            except (json.JSONDecodeError, TypeError):
                return None
        else:  # string
            return self.preference_value
    
    def __repr__(self) -> str:
        return f"<UserPreference {self.user_id}:{self.preference_key}={self.preference_value}>"