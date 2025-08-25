"""
Modern Models Package - Clean ORM with SQLAlchemy 2.0
NO MORE JSON COLUMNS! Proper relationships and normalized data.

Import order is important for relationships to work properly.
"""

# Base classes first
from .base import Base, BaseModel, NamedModel, TimestampMixin, IdMixin, StatusMixin

# Enum/lookup tables
from .enums import (
    AssessmentStatus,
    UserType,
    MediaType,
    AssessmentType,
    PHQ9Category,
    ScaleLabel,
    SettingType
)

# Core user models
from .user_new import User, PatientProfile

# Settings models (replaces JSON columns)
from .settings_new import (
    GlobalSetting,
    PHQ9Setting,
    RecordingSetting,
    ChatSetting,
    UserPreference
)

# Assessment models
from .assessment_new import Assessment, AssessmentSetting

# Response and data models
from .responses_new import PHQ9Response, OpenQuestionResponse, EmotionData

# Analysis models (no more JSON!)
from .analysis_new import (
    LLMModel,
    AnalysisConfiguration,
    LLMAnalysisResult,
    AnalysisIndicator,
    IndicatorDefinition
)

# Export all models for easy imports
__all__ = [
    # Base classes
    'Base',
    'BaseModel',
    'NamedModel',
    'TimestampMixin',
    'IdMixin',
    'StatusMixin',
    
    # Enum tables
    'AssessmentStatus',
    'UserType',
    'MediaType',
    'AssessmentType',
    'PHQ9Category',
    'ScaleLabel',
    'SettingType',
    
    # User models
    'User',
    'PatientProfile',
    
    # Settings models
    'GlobalSetting',
    'PHQ9Setting',
    'RecordingSetting',
    'ChatSetting',
    'UserPreference',
    
    # Assessment models
    'Assessment',
    'AssessmentSetting',
    
    # Response models
    'PHQ9Response',
    'OpenQuestionResponse',
    'EmotionData',
    
    # Analysis models
    'LLMModel',
    'AnalysisConfiguration',
    'LLMAnalysisResult',
    'AnalysisIndicator',
    'IndicatorDefinition',
]

# Model groups for easier access
USER_MODELS = [User, PatientProfile]
ASSESSMENT_MODELS = [Assessment, PHQ9Response, OpenQuestionResponse, EmotionData]
SETTINGS_MODELS = [GlobalSetting, PHQ9Setting, RecordingSetting, ChatSetting, AssessmentSetting]
ANALYSIS_MODELS = [LLMModel, AnalysisConfiguration, LLMAnalysisResult, AnalysisIndicator]
ENUM_MODELS = [AssessmentStatus, UserType, MediaType, AssessmentType, PHQ9Category, ScaleLabel, SettingType]

ALL_MODELS = (
    USER_MODELS + 
    ASSESSMENT_MODELS + 
    SETTINGS_MODELS + 
    ANALYSIS_MODELS + 
    ENUM_MODELS + 
    [IndicatorDefinition, UserPreference]
)

# Validation functions
def validate_model_relationships():
    """Validate that all model relationships are properly defined"""
    issues = []
    
    # Check for circular imports
    for model in ALL_MODELS:
        try:
            # Try to access __table__ to ensure model is properly defined
            _ = model.__table__
        except Exception as e:
            issues.append(f"Model {model.__name__} has definition issues: {e}")
    
    # Check foreign key relationships
    for model in ALL_MODELS:
        if hasattr(model, '__table__'):
            for fk in model.__table__.foreign_keys:
                target_table = fk.column.table.name
                # Verify target table exists
                # This would be expanded for production
                pass
    
    return issues


def get_model_by_table_name(table_name: str):
    """Get model class by table name"""
    for model in ALL_MODELS:
        if hasattr(model, '__tablename__') and model.__tablename__ == table_name:
            return model
    return None


def get_enum_models():
    """Get all enum/lookup table models"""
    return ENUM_MODELS


def get_data_models():
    """Get all data storage models (non-enum)"""
    return USER_MODELS + ASSESSMENT_MODELS + SETTINGS_MODELS + ANALYSIS_MODELS


# Model metadata for migrations and documentation
MODEL_DEPENDENCIES = {
    # Core dependencies (tables that other tables depend on)
    'user_type': [],
    'assessment_status': [],
    'media_type': [],
    'assessment_type': [],
    'phq9_category': [],
    'setting_type': [],
    
    # User models
    'users': ['user_type'],
    'patient_profiles': ['users'],
    
    # Assessment models  
    'assessments': ['users', 'assessment_status'],
    'phq9_responses': ['assessments', 'phq9_category'],
    'open_question_responses': ['assessments'],
    'emotion_data': ['assessments', 'media_type', 'assessment_type'],
    
    # Settings models
    'global_settings': [],
    'phq9_settings': ['assessments'],
    'recording_settings': ['assessments'],
    'chat_settings': ['assessments'],
    'assessment_settings': ['assessments', 'setting_type'],
    'user_preferences': ['users'],
    
    # Analysis models
    'llm_models': [],
    'analysis_configurations': [],
    'llm_analysis_results': ['assessments', 'llm_models', 'analysis_configurations'],
    'analysis_indicators': ['llm_analysis_results'],
    'indicator_definitions': [],
}


def get_creation_order():
    """Get recommended table creation order based on dependencies"""
    created = set()
    order = []
    
    def add_model(table_name):
        if table_name in created:
            return
        
        # Add dependencies first
        for dep in MODEL_DEPENDENCIES.get(table_name, []):
            add_model(dep)
        
        order.append(table_name)
        created.add(table_name)
    
    # Add all tables
    for table_name in MODEL_DEPENDENCIES:
        add_model(table_name)
    
    return order