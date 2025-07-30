# app/services/assessment.py
from app import db
from app.models.assessment import Assessment
from app.models.phq import PHQCategory, PHQQuestion
from app.services.settings import SettingsService
import random
from datetime import datetime

class AssessmentException(Exception):
    pass

class AssessmentService:
    
    @staticmethod
    def create_assessment_session(user_id, session_id):
        """Create new assessment session"""
        try:
            # Create initial assessment record
            assessment = Assessment(
                user_id=user_id,
                session_id=session_id,
                assessment_type='consent',
                status='in_progress'
            )
            
            db.session.add(assessment)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise AssessmentException(f"Failed to create assessment session: {str(e)}")
    
    @staticmethod
    def get_image_capture_settings():
        """Get image capture settings for frontend"""
        try:
            settings = SettingsService.get_all_settings()
            return {
                'enabled': settings.get('enable_capture', True),
                'interval': settings.get('capture_interval', 5),
                'quality': settings.get('image_quality', 0.8),
                'resolution': settings.get('image_resolution', '1280x720')
            }
        except Exception as e:
            raise AssessmentException(f"Failed to get image settings: {str(e)}")
    
    @staticmethod
    def get_randomized_phq_questions():
        """Get one random question per PHQ-9 category"""
        try:
            categories = PHQCategory.query.filter_by(is_active=True).all()
            questions = []
            
            for category in categories:
                # Get all active questions for this category
                active_questions = PHQQuestion.query.filter_by(
                    category_id=category.id,
                    is_active=True
                ).all()
                
                if active_questions:
                    # Pick one random question from this category
                    selected_question = random.choice(active_questions)
                    questions.append({
                        'category': category,
                        'question': selected_question
                    })
            
            # Sort by category number for consistent order
            questions.sort(key=lambda x: x['category'].category_number)
            return questions
            
        except Exception as e:
            raise AssessmentException(f"Failed to get PHQ questions: {str(e)}")
    
    @staticmethod
    def save_assessment_data(session_id, assessment_type, data):
        """Save assessment data to file"""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                assessment_type=assessment_type
            ).first()
            
            if not assessment:
                # Create new assessment record for this type
                assessment = Assessment(
                    session_id=session_id,
                    assessment_type=assessment_type,
                    status='completed'
                )
                db.session.add(assessment)
            
            # TODO: Save data to file system
            # For now, just mark as completed
            assessment.status = 'completed'
            assessment.completed_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise AssessmentException(f"Failed to save assessment data: {str(e)}")
    
    @staticmethod
    def complete_assessment(session_id):
        """Mark entire assessment session as complete"""
        try:
            assessments = Assessment.query.filter_by(session_id=session_id).all()
            
            for assessment in assessments:
                if assessment.status == 'in_progress':
                    assessment.status = 'completed'
                    assessment.completed_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise AssessmentException(f"Failed to complete assessment: {str(e)}")