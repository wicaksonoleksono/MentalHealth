"""
Modern Assessment Model - NO MORE JSON HELL!
Complete rewrite with proper relationships and normalized data
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Assessment(BaseModel):
    """Clean Assessment model with proper relationships (NO JSON columns!)"""
    __tablename__ = 'assessments'
    
    # Foreign key relationships (no more string matching!)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    status_id: Mapped[int] = mapped_column(ForeignKey('assessment_status.id'), nullable=False)
    
    # Unique session identifier
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    
    # Assessment flow tracking (simple booleans)
    phq9_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    open_questions_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Assessment ordering
    first_assessment_type: Mapped[Optional[str]] = mapped_column(String(20))  # 'phq9' or 'open_questions'
    assessment_order: Mapped[Optional[str]] = mapped_column(String(20))  # 'phq_first' or 'questions_first'
    
    # Timestamps (proper datetime fields)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    consent_at: Mapped[Optional[datetime]] = mapped_column()
    camera_check_at: Mapped[Optional[datetime]] = mapped_column()
    first_assessment_started_at: Mapped[Optional[datetime]] = mapped_column()
    
    # PHQ-9 Results
    phq9_score: Mapped[Optional[int]] = mapped_column(Integer)
    phq9_severity: Mapped[Optional[str]] = mapped_column(String(20))  # 'minimal', 'mild', 'moderate', 'severe'
    
    # LLM Analysis status (could be FK to status table)
    llm_analysis_status: Mapped[str] = mapped_column(String(20), default='pending')
    llm_analysis_at: Mapped[Optional[datetime]] = mapped_column()
    
    # Relationships with proper typing
    user: Mapped["User"] = relationship(back_populates="assessments")
    status: Mapped["AssessmentStatus"] = relationship(back_populates="assessments")
    
    # Assessment data relationships (replacing JSON columns!)
    phq9_responses: Mapped[List["PHQ9Response"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    open_responses: Mapped[List["OpenQuestionResponse"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    emotion_data: Mapped[List["EmotionData"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    
    # Settings relationships (NO MORE JSON!)
    settings: Mapped[List["AssessmentSetting"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    
    # Analysis results
    analysis_results: Mapped[List["LLMAnalysisResult"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    
    def mark_first_assessment(self, assessment_type: str) -> None:
        """Mark which assessment type was completed first"""
        if not self.first_assessment_type and not self.first_assessment_started_at:
            self.first_assessment_type = assessment_type
            self.first_assessment_started_at = datetime.utcnow()
    
    def complete_assessment_type(self, assessment_type: str) -> bool:
        """Mark an assessment type as completed and check if fully done"""
        if assessment_type == 'phq9':
            self.phq9_completed = True
        elif assessment_type == 'open_questions':
            self.open_questions_completed = True
        
        # Check if assessment is fully completed
        if self.phq9_completed and self.open_questions_completed:
            self.completed_at = datetime.utcnow()
            # Update status to completed (assuming status_id 2 is completed)
            # This should be handled by service layer
            return True
        
        return False
    
    def get_completion_status(self) -> dict:
        """Get assessment completion status"""
        return {
            'first_type': self.first_assessment_type,
            'phq9_completed': self.phq9_completed,
            'open_questions_completed': self.open_questions_completed,
            'both_completed': self.phq9_completed and self.open_questions_completed,
            'completion_percentage': self.calculate_completion_percentage()
        }
    
    def calculate_completion_percentage(self) -> int:
        """Calculate completion percentage"""
        total_steps = 4  # consent, camera, phq9, open_questions
        completed_steps = 0
        
        if self.consent_agreed:
            completed_steps += 1
        if self.camera_verified:
            completed_steps += 1
        if self.phq9_completed:
            completed_steps += 1
        if self.open_questions_completed:
            completed_steps += 1
        
        return int((completed_steps / total_steps) * 100)
    
    def get_setting_value(self, setting_key: str, default=None):
        """Get a setting value by key (replaces JSON getter methods)"""
        for setting in self.settings:
            if setting.setting_type.name == setting_key:
                return setting.get_typed_value()
        return default
    
    def set_setting_value(self, setting_key: str, value) -> None:
        """Set a setting value by key (replaces JSON setter methods)"""
        # This should be handled by service layer to create AssessmentSetting records
        # Left as placeholder for interface compatibility
        pass
    
    @property
    def is_completed(self) -> bool:
        """Check if assessment is completed"""
        return self.phq9_completed and self.open_questions_completed
    
    @property
    def is_in_progress(self) -> bool:
        """Check if assessment is in progress"""
        return self.status.name == 'in_progress'
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Get assessment duration in minutes"""
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None
    
    def __repr__(self) -> str:
        return f"<Assessment {self.session_id} - User {self.user_id} - {self.status.name if self.status else 'Unknown'}>"


class AssessmentSetting(BaseModel):
    """Individual setting for an assessment - replaces JSON columns!"""
    __tablename__ = 'assessment_settings'
    
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    setting_type_id: Mapped[int] = mapped_column(ForeignKey('setting_type.id'), nullable=False)
    
    # Store the actual value as text and convert based on setting type
    value: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(back_populates="settings")
    setting_type: Mapped["SettingType"] = relationship(back_populates="assessment_settings")
    
    def get_typed_value(self):
        """Get value converted to proper type based on setting_type"""
        if not self.value:
            return None
        
        data_type = self.setting_type.data_type
        
        if data_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'int':
            try:
                return int(self.value)
            except ValueError:
                return None
        elif data_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return None
        elif data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return None
        else:  # string or any other type
            return self.value
    
    def set_typed_value(self, value) -> None:
        """Set value from typed value"""
        if value is None:
            self.value = None
        elif isinstance(value, (dict, list)):
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)
    
    def __repr__(self) -> str:
        return f"<AssessmentSetting {self.setting_type.name}: {self.value}>"