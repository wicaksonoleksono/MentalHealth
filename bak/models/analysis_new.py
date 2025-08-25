"""
Modern LLM Analysis Models - NO MORE JSON parsed_results!
Proper normalized analysis data with queryable indicators
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, StatusMixin, NamedModel


class LLMModel(BaseModel, StatusMixin):
    """LLM model configuration with better metadata"""
    __tablename__ = 'llm_models'
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "openai", "anthropic", "together"
    model_version: Mapped[Optional[str]] = mapped_column(String(50))  # "gpt-4o-mini", "claude-3.5-sonnet"
    
    # Model capabilities and configuration
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    cost_per_token: Mapped[Optional[float]] = mapped_column(Float)  # For cost tracking
    
    # API configuration
    api_key_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Performance metrics
    average_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    success_rate: Mapped[Optional[float]] = mapped_column(Float)  # 0.0 to 1.0
    
    # Relationships
    analysis_results: Mapped[List["LLMAnalysisResult"]] = relationship(
        back_populates="llm_model", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<LLMModel {self.name} ({self.provider})>"


class AnalysisConfiguration(BaseModel):
    """Analysis prompt configuration with versioning"""
    __tablename__ = 'analysis_configurations'
    
    instruction_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    format_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Versioning
    version: Mapped[str] = mapped_column(String(20), default='1.0')
    changelog: Mapped[Optional[str]] = mapped_column(Text)
    
    # Configuration metadata
    created_by: Mapped[Optional[str]] = mapped_column(String(100))  # Username
    temperature: Mapped[float] = mapped_column(Float, default=0.1)
    max_tokens: Mapped[int] = mapped_column(Integer, default=500)
    
    # Relationships
    analysis_results: Mapped[List["LLMAnalysisResult"]] = relationship(back_populates="configuration")
    
    @classmethod
    def get_active_config(cls):
        """Get the current active analysis configuration"""
        return cls.query.filter_by(is_active=True).first()
    
    def __repr__(self) -> str:
        return f"<AnalysisConfiguration v{self.version} - Active: {self.is_active}>"


class LLMAnalysisResult(BaseModel):
    """Analysis results WITHOUT JSON parsed_results - proper relationships!"""
    __tablename__ = 'llm_analysis_results'
    
    # Main relationships
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'), nullable=False)
    llm_model_id: Mapped[int] = mapped_column(ForeignKey('llm_models.id'), nullable=False)
    configuration_id: Mapped[int] = mapped_column(ForeignKey('analysis_configurations.id'), nullable=False)
    
    # Session reference (for easy lookup)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Analysis input data
    chat_history: Mapped[Optional[str]] = mapped_column(Text)  # The conversation analyzed
    phq9_data: Mapped[Optional[str]] = mapped_column(Text)  # PHQ9 responses (JSON)
    
    # Analysis execution
    analysis_status: Mapped[str] = mapped_column(String(20), default='pending')  # 'pending', 'completed', 'failed'
    raw_response: Mapped[Optional[str]] = mapped_column(Text)  # Raw LLM response
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Performance metrics
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    token_usage: Mapped[Optional[int]] = mapped_column(Integer)
    cost_cents: Mapped[Optional[int]] = mapped_column(Integer)  # Cost in cents
    
    # Analysis completion
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    
    # Relationships (NO MORE JSON!)
    assessment: Mapped["Assessment"] = relationship(back_populates="analysis_results")
    llm_model: Mapped["LLMModel"] = relationship(back_populates="analysis_results")
    configuration: Mapped["AnalysisConfiguration"] = relationship(back_populates="analysis_results")
    indicators: Mapped[List["AnalysisIndicator"]] = relationship(
        back_populates="analysis_result", cascade="all, delete-orphan"
    )
    
    @property
    def is_completed(self) -> bool:
        """Check if analysis is completed successfully"""
        return self.analysis_status == 'completed'
    
    @property
    def indicator_count(self) -> int:
        """Get count of indicators"""
        return len(self.indicators)
    
    def get_indicator_value(self, indicator_name: str) -> Optional[float]:
        """Get specific indicator value"""
        for indicator in self.indicators:
            if indicator.indicator_name == indicator_name:
                return indicator.score
        return None
    
    def get_indicators_dict(self) -> dict:
        """Get all indicators as dictionary (for compatibility)"""
        return {
            indicator.indicator_name: {
                'score': indicator.score,
                'confidence': indicator.confidence,
                'reasoning': indicator.reasoning
            }
            for indicator in self.indicators
        }
    
    def __repr__(self) -> str:
        return f"<LLMAnalysisResult {self.session_id} - {self.llm_model.name if self.llm_model else 'Unknown'} - {self.analysis_status}>"


class AnalysisIndicator(BaseModel):
    """Individual analysis indicators - replaces JSON parsed_results!"""
    __tablename__ = 'analysis_indicators'
    
    # Relationship to analysis result
    analysis_result_id: Mapped[int] = mapped_column(ForeignKey('llm_analysis_results.id'), nullable=False)
    
    # Indicator data
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[Optional[float]] = mapped_column(Float)  # The main score/value
    confidence: Mapped[Optional[float]] = mapped_column(Float)  # Confidence level 0.0-1.0
    reasoning: Mapped[Optional[str]] = mapped_column(Text)  # Why this score was given
    
    # Metadata
    data_type: Mapped[str] = mapped_column(String(20), default='float')  # 'float', 'int', 'bool', 'string'
    category: Mapped[Optional[str]] = mapped_column(String(50))  # 'emotional', 'behavioral', 'cognitive'
    severity_level: Mapped[Optional[str]] = mapped_column(String(20))  # 'low', 'medium', 'high'
    
    # Range information (for validation)
    min_value: Mapped[Optional[float]] = mapped_column(Float)
    max_value: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationship
    analysis_result: Mapped["LLMAnalysisResult"] = relationship(back_populates="indicators")
    
    @property
    def normalized_score(self) -> Optional[float]:
        """Get score normalized to 0-1 range"""
        if self.score is None or self.min_value is None or self.max_value is None:
            return None
        
        if self.max_value == self.min_value:
            return 0.5
        
        return (self.score - self.min_value) / (self.max_value - self.min_value)
    
    @property
    def score_percentage(self) -> Optional[int]:
        """Get score as percentage"""
        normalized = self.normalized_score
        if normalized is not None:
            return int(normalized * 100)
        return None
    
    def __repr__(self) -> str:
        return f"<AnalysisIndicator {self.indicator_name}: {self.score} (conf: {self.confidence})>"


class IndicatorDefinition(NamedModel):
    """Definitions for analysis indicators - for consistency and validation"""
    __tablename__ = 'indicator_definitions'
    
    # Definition details
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Value constraints
    min_value: Mapped[Optional[float]] = mapped_column(Float)
    max_value: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(20))  # 'score', 'percentage', 'count'
    
    # Interpretation guidelines
    interpretation_guide: Mapped[Optional[str]] = mapped_column(Text)
    severity_thresholds: Mapped[Optional[str]] = mapped_column(Text)  # JSON of thresholds
    
    # Clinical relevance
    clinical_significance: Mapped[Optional[str]] = mapped_column(String(20))  # 'high', 'medium', 'low'
    research_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<IndicatorDefinition {self.name} ({self.category})>"