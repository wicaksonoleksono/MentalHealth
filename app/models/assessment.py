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
    def __repr__(self):
        return f'<Assessment {self.session_id} - User {self.user_id}>'
class PHQ9Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # 1-9
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

class EmotionData(db.Model):
    # TODO: There is 2 types of stuff video and images.
    # we save The images or video and timestemp it .
    # 
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    assessment_type = db.Column(db.String(20), nullable=False)  # 'phq9' or 'open_questions'
    question_identifier = db.Column(db.String(50))  # PHQ9 question number or open question ID
    pth = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    question_start_time = db.Column(db.DateTime)
    def __repr__(self):
        return f'<EmotionData {self.dominant_emotion} - {self.assessment_type}>'