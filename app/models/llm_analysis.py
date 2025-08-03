# app/models/llm_analysis.py
from datetime import datetime
from app import db
import json

class LLMModel(db.Model):
    """Store configured LLM models for analysis"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "gpt-4o-mini", "claude-3.5-sonnet"
    provider = db.Column(db.String(50), nullable=False)  # "openai", "anthropic", "together"
    is_active = db.Column(db.Boolean, default=True)
    api_key_configured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    analysis_results = db.relationship('LLMAnalysisResult', backref='llm_model', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<LLMModel {self.name} ({self.provider})>'

class LLMAnalysisResult(db.Model):
    """Store analysis results for each session and LLM model"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)  # Assessment session_id
    llm_model_id = db.Column(db.Integer, db.ForeignKey('llm_model.id'), nullable=False)
    
    # Analysis data
    chat_history = db.Column(db.Text)  # The conversation data analyzed
    analysis_prompt = db.Column(db.Text)  # The instruction prompt used
    format_prompt = db.Column(db.Text)  # The format prompt used
    raw_response = db.Column(db.Text)  # Raw LLM response
    parsed_results = db.Column(db.Text)  # JSON string of parsed indicator scores
    
    # Metadata
    analysis_status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    error_message = db.Column(db.Text)  # Error details if failed
    processing_time_ms = db.Column(db.Integer)  # Time taken for analysis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def get_parsed_results(self):
        """Get parsed results as dictionary"""
        if self.parsed_results:
            try:
                return json.loads(self.parsed_results)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_parsed_results(self, results_dict):
        """Set parsed results from dictionary"""
        self.parsed_results = json.dumps(results_dict, ensure_ascii=False, indent=2)
    
    def __repr__(self):
        return f'<LLMAnalysisResult {self.session_id} - {self.llm_model.name if self.llm_model else "Unknown"}>'

class AnalysisConfiguration(db.Model):
    """Store analysis prompt configuration"""
    id = db.Column(db.Integer, primary_key=True)
    instruction_prompt = db.Column(db.Text, nullable=False)  # The analysis instruction prompt
    format_prompt = db.Column(db.Text, nullable=False)  # The JSON format prompt
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_active_config(cls):
        """Get the current active analysis configuration"""
        return cls.query.filter_by(is_active=True).first()
    
    def __repr__(self):
        return f'<AnalysisConfiguration {self.id} - Active: {self.is_active}>'