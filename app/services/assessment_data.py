# app/services/assessment_data.py

import json
from datetime import datetime
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse, EmotionData
from app.models.settings import SettingsKey
from app.services.settings import SettingsService

class AssessmentDataService:
    """Service for consistent access to assessment data and settings"""
    
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
            'assessment': AssessmentDataService._format_assessment_info(assessment),
            'phq9_data': AssessmentDataService._get_phq9_data(assessment),
            'chat_data': AssessmentDataService._get_chat_data(assessment),
            'media_data': AssessmentDataService._get_media_data(assessment),
            'settings_used': AssessmentDataService._get_settings_used(assessment),
            'current_settings': AssessmentDataService._get_current_settings()
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
                'severity': assessment.phq9_severity,
                'completed': assessment.phq9_completed
            }
        }
        
        for response in responses:
            phq9_data['responses'].append({
                'id': response.id,
                'question_number': response.question_number,
                'question_index_in_category': response.question_index_in_category,
                'question_text': response.question_text,
                'response_value': response.response_value,
                'response_time_ms': response.response_time_ms,
                'created_at': response.created_at.isoformat() if response.created_at else None
            })
        
        return phq9_data
    
    @staticmethod
    def _get_chat_data(assessment):
        """Get chat conversation data"""
        chat_responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).all()
        
        chat_data = {
            'conversations': [],
            'exchanges': [],
            'summary': {
                'total_responses': len(chat_responses),
                'completed': assessment.open_questions_completed
            }
        }
        
        for response in chat_responses:
            response_data = {
                'id': response.id,
                'question_text': response.question_text,
                'response_text': response.response_text,
                'response_time_ms': response.response_time_ms,
                'created_at': response.created_at.isoformat() if response.created_at else None
            }
            
            # Categorize complete conversations vs individual exchanges
            if response.question_text == "Complete LangChain Conversation":
                try:
                    conversation_metadata = json.loads(response.response_text)
                    chat_data['conversations'].append({
                        **response_data,
                        'metadata': conversation_metadata
                    })
                except json.JSONDecodeError:
                    chat_data['conversations'].append(response_data)
            else:
                chat_data['exchanges'].append(response_data)
        
        return chat_data
    
    @staticmethod
    def _get_media_data(assessment):
        """Get emotion capture media data"""
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
        return {
            'phq9_settings': assessment.get_phq9_settings(),
            'recording_settings': assessment.get_recording_settings(),
            'chat_settings': assessment.get_chat_settings()
        }
    
    @staticmethod
    def _get_current_settings():
        """Get current system settings for comparison"""
        try:
            return {
                'phq9_settings': SettingsService.get_phq9_config(),
                'recording_settings': SettingsService.get_recording_config(),
                'chat_settings': {
                    'openquestion_prompt': SettingsService.get(SettingsKey.OPENQUESTION_PROMPT),
                    'openquestion_instructions': SettingsService.get(SettingsKey.OPENQUESTION_INSTRUCTIONS)
                }
            }
        except:
            return {}
    
    @staticmethod
    def get_assessment_summary(session_id, user_id=None):
        """Get a summary of assessment for quick access"""
        complete_data = AssessmentDataService.get_complete_assessment_data(session_id, user_id)
        if not complete_data:
            return None
        
        return {
            'session_id': session_id,
            'status': complete_data['assessment']['status'],
            'completion': {
                'phq9_completed': complete_data['assessment']['phq9_completed'],
                'chat_completed': complete_data['assessment']['open_questions_completed'],
                'both_completed': (complete_data['assessment']['phq9_completed'] and 
                                 complete_data['assessment']['open_questions_completed'])
            },
            'results': {
                'phq9_score': complete_data['assessment']['phq9_score'],
                'phq9_severity': complete_data['assessment']['phq9_severity'],
                'total_chat_exchanges': complete_data['chat_data']['summary']['total_responses'],
                'media_files_captured': complete_data['media_data']['summary']['total_files']
            },
            'timestamps': {
                'started_at': complete_data['assessment']['started_at'],
                'completed_at': complete_data['assessment']['completed_at']
            }
        }
    
    @staticmethod
    def export_assessment_data(session_id, user_id=None, format='json'):
        """Export complete assessment data in specified format"""
        complete_data = AssessmentDataService.get_complete_assessment_data(session_id, user_id)
        if not complete_data:
            return None
        
        if format == 'json':
            return json.dumps(complete_data, indent=2, ensure_ascii=False)
        elif format == 'summary':
            return AssessmentDataService.get_assessment_summary(session_id, user_id)
        else:
            return complete_data
