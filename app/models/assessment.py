# app/services/assessment.py - Updated version

from datetime import datetime
from app import db
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse
from app.models.user import User
from app.services.media_file import MediaFileService
import uuid

class AssessmentService:
    @staticmethod
    def create_assessment_session(user_id):
        """Create a new assessment session for a user."""
        session_id = str(uuid.uuid4())
        assessment = Assessment(
            user_id=user_id,
            session_id=session_id,
            started_at=datetime.utcnow()
        )
        db.session.add(assessment)
        db.session.commit()
        return assessment

    @staticmethod
    def record_consent(session_id, user_id):
        """Record consent for an assessment session."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        assessment.consent_agreed = True
        assessment.consent_at = datetime.utcnow()
        db.session.commit()
        return assessment

    @staticmethod
    def record_camera_verification(session_id, user_id):
        """Record camera verification for an assessment session."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        assessment.camera_verified = True
        assessment.camera_check_at = datetime.utcnow()
        db.session.commit()
        return assessment

    @staticmethod
    def start_assessment_type(session_id, user_id, assessment_type):
        """Mark the start of a specific assessment type (PHQ9 or open questions)."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        assessment.mark_first_assessment(assessment_type)
        return assessment

    @staticmethod
    def save_phq9_response(session_id, user_id, question_number, response_value, response_time_ms=None):
        """Save a PHQ-9 response."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")

        # Check if response already exists
        existing_response = PHQ9Response.query.filter_by(
            assessment_id=assessment.id,
            question_number=question_number
        ).first()
        
        if existing_response:
            existing_response.response_value = response_value
            existing_response.response_time_ms = response_time_ms
        else:
            response = PHQ9Response(
                assessment_id=assessment.id,
                question_number=question_number,
                response_value=response_value,
                response_time_ms=response_time_ms
            )
            db.session.add(response)
        
        db.session.commit()
        return assessment

    @staticmethod
    def complete_phq9_assessment(session_id, user_id):
        """Mark PHQ-9 assessment as completed and calculate score."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")

        # Calculate PHQ-9 score
        responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
        total_score = sum(response.response_value for response in responses)
        
        # Determine severity
        if total_score >= 20:
            severity = 'severe'
        elif total_score >= 15:
            severity = 'moderate'
        elif total_score >= 10:
            severity = 'mild'
        elif total_score >= 5:
            severity = 'mild'
        else:
            severity = 'minimal'

        assessment.phq9_score = total_score
        assessment.phq9_severity = severity
        assessment.complete_assessment_type('phq9')
        return assessment

    @staticmethod
    def save_open_question_response(session_id, user_id, question_text, response_text, response_time_ms=None):
        """Save an open question response."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")

        response = OpenQuestionResponse(
            assessment_id=assessment.id,
            question_text=question_text,
            response_text=response_text,
            response_time_ms=response_time_ms
        )
        db.session.add(response)
        db.session.commit()
        return assessment

    @staticmethod
    def complete_open_questions_assessment(session_id, user_id):
        """Mark open questions assessment as completed."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        assessment.complete_assessment_type('open_questions')
        return assessment

    @staticmethod
    def delete_assessment_session(session_id, user_id):
        """Delete assessment session and all associated data including files."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        # Delete all associated files first
        deleted_files = MediaFileService.cleanup_session_files(session_id, user_id)
        
        # Delete database records (cascading will handle related records)
        db.session.delete(assessment)
        db.session.commit()
        
        return {
            'assessment_deleted': True,
            'files_deleted': deleted_files
        }

    @staticmethod
    def get_assessment_summary(session_id, user_id):
        """Get complete assessment summary including file information."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        # Get file information
        files = MediaFileService.get_session_files(session_id, user_id)
        file_validation = MediaFileService.validate_session_files(session_id, user_id)
        
        # Get responses
        phq9_responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
        open_responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).all()
        
        return {
            'assessment': {
                'session_id': assessment.session_id,
                'status': assessment.status,
                'started_at': assessment.started_at,
                'completed_at': assessment.completed_at,
                'phq9_score': assessment.phq9_score,
                'phq9_severity': assessment.phq9_severity,
                'completion_order': assessment.get_completion_order()
            },
            'files': {
                'total_files': len(files),
                'total_size': sum(f['file_size'] for f in files if f['file_size']),
                'validation': file_validation,
                'files_by_type': {
                    'images': [f for f in files if f['media_type'] == 'image'],
                    'videos': [f for f in files if f['media_type'] == 'video']
                }
            },
            'responses': {
                'phq9_count': len(phq9_responses),
                'open_questions_count': len(open_responses)
            }
        }
    @staticmethod
    def get_assessment_statistics():
        """Get statistics about assessment completion patterns."""
        total_assessments = Assessment.query.count()
        completed_assessments = Assessment.query.filter_by(status='completed').count()
        phq9_first = Assessment.query.filter_by(first_assessment_type='phq9').count()
        open_questions_first = Assessment.query.filter_by(first_assessment_type='open_questions').count()
        phq9_completed = Assessment.query.filter_by(phq9_completed=True).count()
        open_questions_completed = Assessment.query.filter_by(open_questions_completed=True).count()
        
        return {
            'total_assessments': total_assessments,
            'completed_assessments': completed_assessments,
            'completion_rate': (completed_assessments / total_assessments * 100) if total_assessments > 0 else 0,
            'first_assessment_stats': {
                'phq9_first': phq9_first,
                'open_questions_first': open_questions_first,
                'phq9_first_percentage': (phq9_first / (phq9_first + open_questions_first) * 100) if (phq9_first + open_questions_first) > 0 else 0
            },
            'completion_stats': {
                'phq9_completed': phq9_completed,
                'open_questions_completed': open_questions_completed
            }
        }

# Legacy method removed: save_emotion_data() 
# Now use MediaFileService.save_emotion_capture() directly in routes
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
