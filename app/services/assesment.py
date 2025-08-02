# app/services/assessment.py - Updated version

from datetime import datetime
from app import db
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse
from app.models.user import User
from app.services.emotion_storage import emotion_storage
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
        deleted_files = emotion_storage.cleanup_session_files(session_id, user_id)
        
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
        files = emotion_storage.get_session_files(session_id, user_id)
        file_validation = emotion_storage.validate_session_files(session_id, user_id)
        
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
        
        # First assessment type statistics
        phq9_first = Assessment.query.filter_by(first_assessment_type='phq9').count()
        open_questions_first = Assessment.query.filter_by(first_assessment_type='open_questions').count()
        
        # Completion rates
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
# Additional helper methods for settings integration

    @staticmethod
    def get_assessment_configuration():
        """Get current assessment configuration from settings for both PHQ and OpenAI services."""
        from app.services.phq import PHQService
        from app.services.openai_chat import OpenAIChatService
        from app.services.settings import SettingsService
        
        try:
            phq_settings = PHQService.get_phq_settings()
            chat_settings = OpenAIChatService.get_chat_settings()
            recording_config = SettingsService.get_recording_config()
            
            return {
                'phq9': {
                    'total_questions': phq_settings['total_questions'],
                    'questions_per_page': phq_settings['questions_per_page'],
                    'randomize_questions': phq_settings['randomize_questions'],
                    'show_progress': phq_settings['show_progress'],
                    'has_custom_categories': len(phq_settings['active_categories']) > 0
                },
                'open_questions': {
                    'has_prompt': bool(chat_settings.get('openquestion_prompt')),
                    'has_instructions': bool(chat_settings.get('instructions')),
                    'enable_followup': chat_settings.get('enable_followup', True)
                },
                'recording': {
                    'enabled': recording_config['enabled'],
                    'mode': recording_config['mode'],
                    'resolution': recording_config['resolution']
                }
            }
        except Exception as e:
            return {
                'error': str(e),
                'phq9': {'total_questions': 0, 'has_custom_categories': False},
                'open_questions': {'has_prompt': False},
                'recording': {'enabled': False}
            }

# Legacy method removed: save_emotion_data() 
# Now use emotion_storage.save_video() or emotion_storage.save_image() directly in routes