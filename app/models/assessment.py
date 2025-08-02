# app/models/assessment.py
from datetime import datetime
from app import db

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    # Assessment flow tracking
    first_assessment_type = db.Column(db.String(20))  # 'phq9' or 'open_questions'
    phq9_completed = db.Column(db.Boolean, default=False)
    open_questions_completed = db.Column(db.Boolean, default=False)
    # Assessment status
    status = db.Column(db.String(20), default='in_progress')  # 'in_progress', 'completed', 'abandoned'
    consent_agreed = db.Column(db.Boolean, default=False)
    camera_verified = db.Column(db.Boolean, default=False)
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    consent_at = db.Column(db.DateTime)
    camera_check_at = db.Column(db.DateTime)
    first_assessment_started_at = db.Column(db.DateTime)
    # Results
    phq9_score = db.Column(db.Integer)
    phq9_severity = db.Column(db.String(20))  # 'minimal', 'mild', 'moderate', 'severe'
    # Settings used during assessment (JSON)
    phq9_settings = db.Column(db.Text)  # JSON string of PHQ-9 settings used
    recording_settings = db.Column(db.Text)  # JSON string of recording settings used
    chat_settings = db.Column(db.Text)  # JSON string of chat settings used
    assessment_order = db.Column(db.String(20))  # 'phq_first' or 'questions_first'
    # Relationships
    phq9_responses = db.relationship('PHQ9Response', backref='assessment', lazy=True, cascade='all, delete-orphan')
    open_responses = db.relationship('OpenQuestionResponse', backref='assessment', lazy=True, cascade='all, delete-orphan')
    emotion_data = db.relationship('EmotionData', backref='assessment', lazy=True, cascade='all, delete-orphan')
    def mark_first_assessment(self, assessment_type):
        """Mark which assessment type was completed first."""
        if not self.first_assessment_type and not self.first_assessment_started_at:
            self.first_assessment_type = assessment_type
            self.first_assessment_started_at = datetime.utcnow()
            db.session.commit()
    def complete_assessment_type(self, assessment_type):
        if assessment_type == 'phq9':
            self.phq9_completed = True
        elif assessment_type == 'open_questions':
            self.open_questions_completed = True
        if self.phq9_completed and self.open_questions_completed:
            self.status = 'completed'
            self.completed_at = datetime.utcnow()
        db.session.commit()
        
    def get_completion_order(self):
            return {
                'first_type': self.first_assessment_type,
                'phq9_completed': self.phq9_completed,
                'open_questions_completed': self.open_questions_completed,
                'both_completed': self.phq9_completed and self.open_questions_completed
            }
    def set_phq9_settings(self, settings_dict):
        """Store PHQ-9 settings as JSON"""
        import json
        self.phq9_settings = json.dumps(settings_dict, ensure_ascii=False)
    
    def get_phq9_settings(self):
        """Retrieve PHQ-9 settings from JSON"""
        import json
        if self.phq9_settings:
            try:
                return json.loads(self.phq9_settings)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_recording_settings(self, settings_dict):
        """Store recording settings as JSON"""
        import json
        self.recording_settings = json.dumps(settings_dict, ensure_ascii=False)
    
    def get_recording_settings(self):
        """Retrieve recording settings from JSON"""
        import json
        if self.recording_settings:
            try:
                return json.loads(self.recording_settings)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_chat_settings(self, settings_dict):
        """Store chat settings as JSON"""
        import json
        self.chat_settings = json.dumps(settings_dict, ensure_ascii=False)
    
    def get_chat_settings(self):
        """Retrieve chat settings from JSON"""
        import json
        if self.chat_settings:
            try:
                return json.loads(self.chat_settings)
            except json.JSONDecodeError:
                return {}
        return {}

    def __repr__(self):
        return f'<Assessment {self.session_id} - User {self.user_id}>'
class PHQ9Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # Category number (1-20)
    question_index_in_category = db.Column(db.Integer, default=0)  # Index within category (0,1,2...)
    question_text = db.Column(db.Text)  # Store the actual question text
    response_value = db.Column(db.Integer, nullable=False)   # 0-3
    response_time_ms = db.Column(db.Integer)  # Time taken to answer in milliseconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PHQ9Response Q{self.question_number}: {self.response_value}>'
class OpenQuestionResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text)
    response_time_ms = db.Column(db.Integer)  # Time taken to answer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<OpenQuestionResponse {self.id}>'

# app/models/assessment.py - EmotionData class only (replace existing)

class EmotionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    assessment_type = db.Column(db.String(20), nullable=False)  # 'phq9' or 'open_questions'
    question_identifier = db.Column(db.String(50))  # PHQ9 question number or open question ID
    media_type = db.Column(db.String(10), nullable=False)  # 'image' or 'video'
    file_path = db.Column(db.String(255), nullable=False)  # Relative path from uploads root
    original_filename = db.Column(db.String(100))
    file_size = db.Column(db.Integer)  # File size in bytes
    mime_type = db.Column(db.String(50))  # image/jpeg, video/webm, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    question_start_time = db.Column(db.DateTime)
    duration_ms = db.Column(db.Integer)  # For videos or capture duration
    resolution = db.Column(db.String(20))  # "1280x720"
    quality_setting = db.Column(db.Float)  # 0.8 for images, etc.
    def __repr__(self):
        return f'<EmotionData {self.media_type} - {self.assessment_type} - {self.file_path}>'
    def get_full_path(self):
        """Get absolute file path"""
        from flask import current_app
        import os
        return os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), self.file_path)
    
    def file_exists(self):
        """Check if the physical file exists"""
        import os
        return os.path.exists(self.get_full_path())

# app/models/phq.py
from enum import Enum

class PHQCategoryType(Enum):
    ANHEDONIA = (1, "Anhedonia", "Loss of interest or pleasure", "Kurang tertarik atau bergairah dalam melakukan apapun")
    DEPRESSED_MOOD = (2, "Depressed Mood", "Feeling down, depressed, or hopeless", "Merasa murung, muram, atau putus asa")
    SLEEP_DISTURBANCE = (3, "Sleep Disturbance", "Insomnia or hypersomnia", "Sulit tidur atau mudah terbangun, atau terlalu banyak tidur")
    FATIGUE = (4, "Fatigue", "Loss of energy or tiredness", "Merasa lelah atau kurang bertenaga")
    APPETITE_CHANGES = (5, "Appetite Changes", "Weight/appetite fluctuations", "Kurang nafsu makan atau terlalu banyak makan")
    WORTHLESSNESS = (6, "Worthlessness", "Feelings of guilt or failure", "Kurang percaya diri — atau merasa bahwa Anda adalah orang yang gagal atau telah mengecewakan diri sendiri atau keluarga")
    CONCENTRATION = (7, "Concentration", "Difficulty focusing or thinking", "Sulit berkonsentrasi pada sesuatu, misalnya membaca koran atau menonton televisi")
    PSYCHOMOTOR = (8, "Psychomotor", "Agitation or retardation", "Bergerak atau berbicara sangat lambat sehingga orang lain memperhatikannya. Atau sebaliknya — merasa resah atau gelisah sehingga Anda lebih sering bergerak dari biasanya")
    SUICIDAL_IDEATION = (9, "Suicidal Ideation", "Thoughts of death or self-harm", "Merasa lebih baik mati atau ingin melukai diri sendiri dengan cara apapun")

    @property
    def number(self):
        return self.value[0]

    @property
    def name(self):
        return self.value[1]

    @property
    def description(self):
        return self.value[2]
    
    @property
    def default_question(self):
        return self.value[3]

    @classmethod
    def get_by_number(cls, number):
        for category in cls:
            if category.number == number:
                return category
        return None

    @classmethod
    def get_all_data(cls):
        """Return all categories as dict for frontend"""
        return [
            {
                'number': cat.number,
                'name': cat.name,
                'description': cat.description,
                'default_question': cat.default_question
            }
            for cat in cls
        ]
