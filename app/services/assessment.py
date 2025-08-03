# app/services/assessment.py - Unified Assessment Service
# Combines patient workflow + admin/export functionality

import json
from datetime import datetime
from app import db
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse, EmotionData
from app.models.user import User
from app.models.settings import SettingsKey
from app.services.emotion_storage import get_emotion_storage
from app.services.settings import SettingsService
import uuid

class AssessmentService:
    """Unified service for assessment workflow and data management"""
    
    # ===================================================================
    # PATIENT WORKFLOW METHODS
    # ===================================================================
    
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
        """Mark the start of a specific assessment type."""
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
        
        # Check if response already exists for this question
        existing_response = PHQ9Response.query.filter_by(
            assessment_id=assessment.id,
            question_index=question_number
        ).first()
        
        if existing_response:
            # Update existing response
            existing_response.response_value = response_value
            existing_response.response_time_ms = response_time_ms
            existing_response.response_timestamp = int(datetime.utcnow().timestamp() * 1000)
        else:
            # Create new response
            response = PHQ9Response(
                assessment_id=assessment.id,
                question_index=question_number,
                response_value=response_value,
                response_time_ms=response_time_ms,
                response_timestamp=int(datetime.utcnow().timestamp() * 1000)
            )
            db.session.add(response)
        
        db.session.commit()
        return assessment

    @staticmethod
    def complete_phq9_assessment(session_id, user_id):
        """Complete the PHQ-9 assessment and calculate score."""
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
        if total_score <= 4:
            severity = 'minimal'
        elif total_score <= 9:
            severity = 'mild'
        elif total_score <= 14:
            severity = 'moderate'
        elif total_score <= 19:
            severity = 'moderately_severe'
        else:
            severity = 'severe'
        
        # Update assessment
        assessment.phq9_completed = True
        assessment.phq9_score = total_score
        assessment.phq9_severity = severity
        assessment.complete_assessment_type('phq9')
        
        db.session.commit()
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
        
        # Get next exchange number
        existing_count = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).count()
        
        response = OpenQuestionResponse(
            assessment_id=assessment.id,
            user_message=question_text,
            ai_response=response_text,
            exchange_number=existing_count + 1,
            response_time_ms=response_time_ms
        )
        db.session.add(response)
        db.session.commit()
        return response

    @staticmethod
    def complete_open_questions_assessment(session_id, user_id):
        """Complete the open questions assessment."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        assessment.open_questions_completed = True
        assessment.complete_assessment_type('open_questions')
        
        db.session.commit()
        return assessment

    @staticmethod
    def delete_assessment_session(session_id, user_id):
        """Delete an assessment session and all related data."""
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        # Delete all associated files first
        deleted_files = get_emotion_storage().cleanup_session_files(session_id, user_id)
        
        # Delete database records (cascading will handle related records)
        db.session.delete(assessment)
        db.session.commit()
        
        return {
            'deleted_files': deleted_files,
            'session_id': session_id
        }

    # ===================================================================
    # ADMIN/EXPORT METHODS
    # ===================================================================

    @staticmethod
    def get_complete_assessment_data(session_id, user_id=None):
        """Get all assessment data including settings, responses, and media"""
        query = Assessment.query.filter_by(session_id=session_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        assessment = query.first()
        if not assessment:
            return None
        
        return {
            'assessment': AssessmentService._format_assessment_info(assessment),
            'phq9_data': AssessmentService._get_phq9_data(assessment),
            'chat_data': AssessmentService._get_chat_data(assessment),
            'media_data': AssessmentService._get_media_data(assessment),
            'settings_used': AssessmentService._get_settings_used(assessment),
            'current_settings': AssessmentService._get_current_settings()
        }

    @staticmethod
    def _format_assessment_info(assessment):
        """Format basic assessment information"""
        return {
            'id': assessment.id,
            'session_id': assessment.session_id,
            'user_id': assessment.user_id,
            'status': assessment.status,
            'assessment_order': assessment.assessment_order,
            'first_assessment_type': assessment.first_assessment_type,
            'phq9_completed': assessment.phq9_completed,
            'open_questions_completed': assessment.open_questions_completed,
            'camera_verified': assessment.camera_verified,
            'consent_agreed': assessment.consent_agreed,
            'started_at': assessment.started_at.isoformat() if assessment.started_at else None,
            'completed_at': assessment.completed_at.isoformat() if assessment.completed_at else None,
            'phq9_score': assessment.phq9_score,
            'phq9_severity': assessment.phq9_severity
        }

    @staticmethod
    def _get_phq9_data(assessment):
        """Get PHQ-9 responses with detailed information"""
        responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
        
        phq9_data = {
            'responses': [],
            'summary': {
                'total_responses': len(responses),
                'total_score': assessment.phq9_score,
                'severity_level': assessment.phq9_severity,
                'completed': assessment.phq9_completed
            }
        }
        
        for response in responses:
            phq9_data['responses'].append({
                'question_index': response.question_index,
                'response_value': response.response_value,
                'response_time_ms': response.response_time_ms,
                'response_timestamp': response.response_timestamp,
                'timestamp': response.timestamp.isoformat() if response.timestamp else None
            })
        
        return phq9_data

    @staticmethod
    def _get_chat_data(assessment):
        """Get open question chat data"""
        responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).order_by(OpenQuestionResponse.exchange_number).all()
        
        chat_data = {
            'exchanges': [],
            'summary': {
                'total_exchanges': len(responses),
                'completed': assessment.open_questions_completed,
                'total_words_user': 0,
                'total_words_ai': 0
            }
        }
        
        total_user_words = 0
        total_ai_words = 0
        
        for response in responses:
            user_words = len(response.user_message.split()) if response.user_message else 0
            ai_words = len(response.ai_response.split()) if response.ai_response else 0
            
            total_user_words += user_words
            total_ai_words += ai_words
            
            chat_data['exchanges'].append({
                'exchange_number': response.exchange_number,
                'user_message': response.user_message,
                'ai_response': response.ai_response,
                'response_time_ms': response.response_time_ms,
                'timestamp': response.timestamp.isoformat() if response.timestamp else None,
                'user_word_count': user_words,
                'ai_word_count': ai_words
            })
        
        chat_data['summary']['total_words_user'] = total_user_words
        chat_data['summary']['total_words_ai'] = total_ai_words
        
        return chat_data

    @staticmethod
    def _get_media_data(assessment):
        """Get media files data"""
        media_files = EmotionData.query.filter_by(assessment_id=assessment.id).all()
        
        media_data = {
            'files': [],
            'summary': {
                'total_files': len(media_files),
                'images': len([f for f in media_files if f.media_type == 'image']),
                'videos': len([f for f in media_files if f.media_type == 'video']),
                'phq9_files': len([f for f in media_files if f.assessment_type == 'phq9']),
                'openq_files': len([f for f in media_files if f.assessment_type == 'open_questions'])
            }
        }
        
        for media_file in media_files:
            media_data['files'].append({
                'id': media_file.id,
                'assessment_type': media_file.assessment_type,
                'question_identifier': media_file.question_identifier,
                'media_type': media_file.media_type,
                'file_path': media_file.file_path,
                'original_filename': media_file.original_filename,
                'file_size': media_file.file_size,
                'mime_type': media_file.mime_type,
                'resolution': media_file.resolution,
                'quality_setting': media_file.quality_setting,
                'duration_ms': media_file.duration_ms,
                'timestamp': media_file.timestamp.isoformat() if media_file.timestamp else None,
                'file_exists': media_file.file_exists()
            })
        
        return media_data

    @staticmethod
    def _get_settings_used(assessment):
        """Get settings that were used during the assessment"""
        settings_used = {}
        
        # Parse stored settings from assessment
        if assessment.phq9_settings:
            try:
                settings_used['phq9'] = json.loads(assessment.phq9_settings)
            except:
                settings_used['phq9'] = {}
        
        if assessment.recording_settings:
            try:
                settings_used['recording'] = json.loads(assessment.recording_settings)
            except:
                settings_used['recording'] = {}
        
        if assessment.chat_settings:
            try:
                settings_used['chat'] = json.loads(assessment.chat_settings)
            except:
                settings_used['chat'] = {}
        
        return settings_used

    @staticmethod
    def _get_current_settings():
        """Get current application settings"""
        return {
            'phq9': SettingsService.get_phq9_settings(),
            'recording': SettingsService.get_recording_settings(),
            'chat': SettingsService.get_chat_settings()
        }

    @staticmethod
    def get_assessment_summary(session_id, user_id=None):
        """Get assessment summary (unified method - no more duplicates!)"""
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            raise ValueError("Assessment session not found")
        
        # Get file information
        files = get_emotion_storage().get_session_files(session_id, user_id or assessment.user_id)
        file_validation = get_emotion_storage().validate_session_files(session_id, user_id or assessment.user_id)
        
        # Get responses
        phq9_responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
        open_responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).all()
        
        return {
            'assessment_info': {
                'session_id': assessment.session_id,
                'user_id': assessment.user_id,
                'status': assessment.status,
                'started_at': assessment.started_at.isoformat() if assessment.started_at else None,
                'completed_at': assessment.completed_at.isoformat() if assessment.completed_at else None,
                'phq9_completed': assessment.phq9_completed,
                'open_questions_completed': assessment.open_questions_completed,
                'phq9_score': assessment.phq9_score,
                'phq9_severity': assessment.phq9_severity
            },
            'response_counts': {
                'phq9_responses': len(phq9_responses),
                'open_question_exchanges': len(open_responses)
            },
            'file_info': {
                'total_files': len(files),
                'files_valid': file_validation.get('is_valid', False),
                'file_details': files
            },
            'file_validation': file_validation
        }

    @staticmethod
    def export_assessment_data(session_id, user_id=None, format='json'):
        """Export assessment data in specified format"""
        complete_data = AssessmentService.get_complete_assessment_data(session_id, user_id)
        if not complete_data:
            return None
        
        if format.lower() == 'json':
            return json.dumps(complete_data, indent=2, default=str)
        elif format.lower() == 'summary':
            return AssessmentService.get_assessment_summary(session_id, user_id)
        else:
            return complete_data

    # ===================================================================
    # SYSTEM STATISTICS
    # ===================================================================

    @staticmethod
    def get_assessment_statistics():
        """Get overall assessment statistics."""
        total_assessments = Assessment.query.count()
        completed_assessments = Assessment.query.filter_by(status='completed').count()
        in_progress_assessments = Assessment.query.filter_by(status='in_progress').count()
        abandoned_assessments = Assessment.query.filter_by(status='abandoned').count()
        
        phq9_completions = Assessment.query.filter_by(phq9_completed=True).count()
        open_question_completions = Assessment.query.filter_by(open_questions_completed=True).count()
        
        return {
            'total_assessments': total_assessments,
            'completed_assessments': completed_assessments,
            'in_progress_assessments': in_progress_assessments,
            'abandoned_assessments': abandoned_assessments,
            'completion_rate': (completed_assessments / total_assessments * 100) if total_assessments > 0 else 0,
            'phq9_completions': phq9_completions,
            'open_question_completions': open_question_completions,
            'average_phq9_score': db.session.query(db.func.avg(Assessment.phq9_score)).filter(Assessment.phq9_score.isnot(None)).scalar() or 0
        }

    @staticmethod
    def get_assessment_configuration():
        """Get current assessment configuration settings."""
        settings = SettingsService.get_all_settings()
        
        return {
            'phq9': {
                'enabled': settings.get('phq9_enabled', True),
                'randomize_order': settings.get('phq9_randomize_order', False),
                'show_progress': settings.get('phq9_show_progress', True)
            },
            'open_questions': {
                'enabled': settings.get('openquestion_enabled', True),
                'max_exchanges': settings.get('openquestion_max_exchanges', 10),
                'ai_model': settings.get('openquestion_ai_model', 'gpt-4')
            },
            'recording': {'enabled': settings.get('enable_recording', False)}
        }