# app/services/assesment.py
from datetime import datetime
from app import db
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse, EmotionData
from app.models.user import User
import uuid


class AssessmentService:
    @staticmethod
    def create_assessment_session(user_id):
        """Create a new assessment session for a user."""
        try:
            session_id = str(uuid.uuid4())
            
            assessment = Assessment(
                user_id=user_id,
                session_id=session_id,
                started_at=datetime.utcnow()
            )
            
            db.session.add(assessment)
            db.session.commit()
            
            return assessment
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def record_consent(session_id, user_id):
        """Record consent for an assessment session."""
        try:
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
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def record_camera_verification(session_id, user_id):
        """Record camera verification for an assessment session."""
        try:
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
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def start_assessment_type(session_id, user_id, assessment_type):
        """Mark the start of a specific assessment type (PHQ9 or open questions)."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Mark as first assessment if none started yet
            assessment.mark_first_assessment(assessment_type)
            
            return assessment
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def save_phq9_response(session_id, user_id, question_number, response_value, response_time_ms=None):
        """Save a PHQ-9 response."""
        try:
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
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def complete_phq9_assessment(session_id, user_id):
        """Mark PHQ-9 assessment as completed and calculate score."""
        try:
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
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def save_open_question_response(session_id, user_id, question_text, response_text, response_time_ms=None):
        """Save an open question response."""
        try:
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
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def complete_open_questions_assessment(session_id, user_id):
        """Mark open questions assessment as completed."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            assessment.complete_assessment_type('open_questions')
            
            return assessment
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def save_emotion_data(session_id, user_id, assessment_type, question_identifier, 
                         dominant_emotion, emotion_confidence, emotions_detected):
        """Save emotion analysis data."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            emotion_data = EmotionData(
                assessment_id=assessment.id,
                assessment_type=assessment_type,
                question_identifier=question_identifier,
                dominant_emotion=dominant_emotion,
                emotion_confidence=emotion_confidence,
                emotions_detected=emotions_detected
            )
            
            db.session.add(emotion_data)
            db.session.commit()
            
            return emotion_data
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_assessment_statistics():
        """Get statistics about assessment completion patterns."""
        try:
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
            
        except Exception as e:
            raise e