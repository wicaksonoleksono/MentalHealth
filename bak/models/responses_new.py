"""
Modern Response Models - Clean relationships and proper data types
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class PHQ9Response(BaseModel):
    """PHQ-9 response with proper category relationship"""
    __tablename__ = 'phq9_responses'
    
    # Relationships
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey('phq9_category.id'), nullable=False)
    
    # Response data
    response_value: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-3 scale
    question_text: Mapped[Optional[str]] = mapped_column(Text)  # The actual question asked
    question_index_in_category: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing data
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    question_started_at: Mapped[Optional[datetime]] = mapped_column()
    response_submitted_at: Mapped[Optional[datetime]] = mapped_column()
    
    # Additional metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # For fraud detection
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(back_populates="phq9_responses")
    category: Mapped["PHQ9Category"] = relationship(back_populates="phq9_responses")
    emotion_captures: Mapped[List["EmotionData"]] = relationship(back_populates="phq9_response")
    
    @property
    def response_duration_ms(self) -> Optional[int]:
        """Calculate response duration"""
        if self.question_started_at and self.response_submitted_at:
            delta = self.response_submitted_at - self.question_started_at
            return int(delta.total_seconds() * 1000)
        return self.response_time_ms
    
    def __repr__(self) -> str:
        return f"<PHQ9Response Assessment:{self.assessment_id} Cat:{self.category.number if self.category else self.category_id} Value:{self.response_value}>"


class OpenQuestionResponse(BaseModel):
    """Open question responses with better structure"""
    __tablename__ = 'open_question_responses'
    
    # Relationships
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    
    # Question and response data
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text)
    question_order: Mapped[int] = mapped_column(Integer, default=1)
    
    # Conversation metadata
    conversation_turn: Mapped[int] = mapped_column(Integer, default=1)  # Which turn in conversation
    is_follow_up: Mapped[bool] = mapped_column(default=False)  # Is this a follow-up question
    parent_response_id: Mapped[Optional[int]] = mapped_column(ForeignKey('open_question_responses.id'))
    
    # Timing data
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    question_started_at: Mapped[Optional[datetime]] = mapped_column()
    response_submitted_at: Mapped[Optional[datetime]] = mapped_column()
    
    # Response quality metrics
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)  # -1 to 1
    
    # Additional metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(back_populates="open_responses")
    parent_response: Mapped[Optional["OpenQuestionResponse"]] = relationship(
        remote_side="OpenQuestionResponse.id", back_populates="follow_up_responses"
    )
    follow_up_responses: Mapped[List["OpenQuestionResponse"]] = relationship(
        back_populates="parent_response"
    )
    emotion_captures: Mapped[List["EmotionData"]] = relationship(back_populates="open_response")
    
    def calculate_metrics(self) -> None:
        """Calculate response quality metrics"""
        if self.response_text:
            self.word_count = len(self.response_text.split())
            self.character_count = len(self.response_text)
            # sentiment_score could be calculated by external service
    
    @property
    def response_duration_ms(self) -> Optional[int]:
        """Calculate response duration"""
        if self.question_started_at and self.response_submitted_at:
            delta = self.response_submitted_at - self.question_started_at
            return int(delta.total_seconds() * 1000)
        return self.response_time_ms
    
    def __repr__(self) -> str:
        return f"<OpenQuestionResponse Assessment:{self.assessment_id} Turn:{self.conversation_turn}>"


class EmotionData(BaseModel):
    """Enhanced emotion data with proper relationships"""
    __tablename__ = 'emotion_data'
    
    # Main relationships
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    assessment_type_id: Mapped[int] = mapped_column(ForeignKey('assessment_type.id'), nullable=False)
    media_type_id: Mapped[int] = mapped_column(ForeignKey('media_type.id'), nullable=False)
    
    # Optional relationships to specific responses
    phq9_response_id: Mapped[Optional[int]] = mapped_column(ForeignKey('phq9_responses.id'))
    open_response_id: Mapped[Optional[int]] = mapped_column(ForeignKey('open_question_responses.id'))
    
    # File information
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Media metadata
    resolution: Mapped[Optional[str]] = mapped_column(String(20))  # "1280x720"
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)  # For videos
    quality_setting: Mapped[Optional[float]] = mapped_column(Float)  # 0.0 to 1.0
    
    # Timing correlation data
    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    question_started_at: Mapped[Optional[datetime]] = mapped_column()
    time_into_question_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Processing status
    processed: Mapped[bool] = mapped_column(default=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Technical metadata (could be JSON for flexibility)
    capture_metadata: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(back_populates="emotion_data")
    assessment_type: Mapped["AssessmentType"] = relationship(back_populates="emotion_data")
    media_type: Mapped["MediaType"] = relationship(back_populates="emotion_data")
    phq9_response: Mapped[Optional["PHQ9Response"]] = relationship(back_populates="emotion_captures")
    open_response: Mapped[Optional["OpenQuestionResponse"]] = relationship(back_populates="emotion_captures")
    
    def get_full_path(self) -> str:
        """Get absolute file path"""
        from flask import current_app
        import os
        return os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), self.file_path)
    
    def file_exists(self) -> bool:
        """Check if the physical file exists"""
        import os
        return os.path.exists(self.get_full_path())
    
    def get_capture_metadata(self) -> dict:
        """Get capture metadata as dict"""
        if self.capture_metadata:
            try:
                import json
                return json.loads(self.capture_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_capture_metadata(self, metadata: dict) -> None:
        """Set capture metadata from dict"""
        if metadata:
            import json
            self.capture_metadata = json.dumps(metadata)
        else:
            self.capture_metadata = None
    
    @property
    def file_extension(self) -> Optional[str]:
        """Get file extension"""
        if self.file_path:
            return self.file_path.split('.')[-1].lower()
        return None
    
    def __repr__(self) -> str:
        return f"<EmotionData {self.media_type.name if self.media_type else 'Unknown'} - Assessment:{self.assessment_id} - {self.file_path}>"