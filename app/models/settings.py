# app/models/settings.py
from app import db
from datetime import datetime
# app/models/settings_keys.py

from enum import Enum

class SettingsKey(Enum):
    # Assessment Text Settings
    OPENQUESTION_PROMPT = ('openquestion_prompt', 'text', 'Open question AI prompt')
    OPENQUESTION_INSTRUCTIONS = ('openquestion_instructions', 'text', 'Open questions instructions')
    CONSENT_FORM_TEXT = ('consent_form_text', 'text', 'Consent form text')
    PHQ9_INSTRUCTIONS = ('phq9_instructions', 'text', 'PHQ9 assessment instructions')
    
    # Recording Settings
    RECORDING_MODE = ('recording_mode', 'choice', 'Recording mode', ['capture', 'video'])
    ENABLE_RECORDING = ('enable_recording', 'boolean', 'Enable camera recording', True)
    CAPTURE_INTERVAL = ('capture_interval', 'integer', 'Image capture interval (seconds)', 5)
    RESOLUTION = ('resolution', 'choice', 'Camera resolution', ['640x480', '1280x720', '1920x1080'])
    
    # Image Settings
    IMAGE_QUALITY = ('image_quality', 'float', 'Image quality (0.1-1.0)', 0.8)
    
    # Video Settings  
    VIDEO_QUALITY = ('video_quality', 'choice', 'Video quality', ['480p', '720p', '1080p'])
    VIDEO_FORMAT = ('video_format', 'choice', 'Video format', ['webm', 'mp4'])
    
    # PHQ9 Scale Settings
    SCALE_MIN = ('scale_min', 'integer', 'Scale minimum value', 0)
    SCALE_MAX = ('scale_max', 'integer', 'Scale maximum value', 3)
    SCALE_LABEL_0 = ('scale_label_0', 'string', 'Scale label for 0', 'Not at all')
    SCALE_LABEL_1 = ('scale_label_1', 'string', 'Scale label for 1', 'Several days')
    SCALE_LABEL_2 = ('scale_label_2', 'string', 'Scale label for 2', 'More than half the days')
    SCALE_LABEL_3 = ('scale_label_3', 'string', 'Scale label for 3', 'Nearly every day')
    
    # PHQ9 Behavior Settings
    PHQ9_RANDOMIZE_QUESTIONS = ('phq9_randomize_questions', 'boolean', 'Randomize PHQ9 questions', False)
    PHQ9_SHOW_PROGRESS = ('phq9_show_progress', 'boolean', 'Show progress bar', True)
    PHQ9_QUESTIONS_PER_PAGE = ('phq9_questions_per_page', 'integer', 'Questions per page', 1)
    
    def __init__(self, key, data_type, description, default=None):
        self.key = key
        self.data_type = data_type
        self.description = description
        self.default = default
    
    @property
    def choices(self):
        """Get choices for choice-type settings"""
        if len(self.value) > 3:
            return self.value[3]
        return None
    
    @classmethod
    def get_by_key(cls, key):
        """Get enum by key string"""
        for setting in cls:
            if setting.key == key:
                return setting
        return None
    
    @classmethod
    def get_recording_settings(cls):
        """Get all recording-related settings"""
        recording_keys = {
            cls.RECORDING_MODE, cls.ENABLE_RECORDING, cls.CAPTURE_INTERVAL,
            cls.RESOLUTION, cls.IMAGE_QUALITY, cls.VIDEO_QUALITY, cls.VIDEO_FORMAT
        }
        return recording_keys
    
    @classmethod
    def get_phq9_settings(cls):
        """Get all PHQ9-related settings"""
        phq9_keys = {
            cls.PHQ9_INSTRUCTIONS, cls.PHQ9_RANDOMIZE_QUESTIONS,
            cls.PHQ9_SHOW_PROGRESS, cls.PHQ9_QUESTIONS_PER_PAGE,
            cls.SCALE_MIN, cls.SCALE_MAX,
            cls.SCALE_LABEL_0, cls.SCALE_LABEL_1, cls.SCALE_LABEL_2, cls.SCALE_LABEL_3
        }
        return phq9_keys
    
    @classmethod
    def get_text_settings(cls):
        """Get all text/content settings"""
        text_keys = {
            cls.OPENQUESTION_PROMPT, cls.OPENQUESTION_INSTRUCTIONS,
            cls.CONSENT_FORM_TEXT, cls.PHQ9_INSTRUCTIONS
        }
        return text_keys
class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)