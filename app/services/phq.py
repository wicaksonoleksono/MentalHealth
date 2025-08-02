# app/services/phq.py
import json
import random
from datetime import datetime
from app import db
from app.models.settings import AppSetting, SettingsKey
from app.models.assessment import Assessment, PHQ9Response
from app.services.assesment import AssessmentService
from app.services.settings import SettingsService


class PHQService:
    @staticmethod
    def get_phq_settings():
        """Get PHQ settings using the same SettingsService used by admin."""
        # Get PHQ9 settings using SettingsService for consistency
        phq9_config = SettingsService.get_phq9_config()
        text_settings = SettingsService.get_group(SettingsKey.get_text_settings)
        
        settings = {
            'instructions': text_settings.get('phq9_instructions', 'Please answer each question based on how you have been feeling over the past two weeks.'),
            'randomize_questions': phq9_config['randomize'],
            'scale_min': phq9_config['scale']['min'],
            'scale_max': phq9_config['scale']['max'],
            'scale_labels': phq9_config['scale']['labels']
        }
        
        # Get active categories and their questions from database
        active_categories = []
        all_questions = []
        
        # Support up to 20 categories as per admin settings
        for cat_num in range(1, 21):
            exists_key = f'phq_category_{cat_num}_exists'
            exists = PHQService._get_raw_setting(exists_key)
            if exists == '1':
                # Get category name
                name_key = f'phq_category_{cat_num}_name'
                category_name = PHQService._get_raw_setting(name_key, f'Category {cat_num}')
                
                # Get questions
                questions_key = f'phq_category_{cat_num}_questions'
                questions_data = PHQService._get_raw_setting(questions_key)
                if questions_data:
                    try:
                        questions = json.loads(questions_data)
                        if not isinstance(questions, list):
                            questions = [questions_data]  # Single string
                    except json.JSONDecodeError:
                        questions = [q.strip() for q in questions_data.split(',') if q.strip()]
                    
                    # Filter out empty questions
                    questions = [q for q in questions if q.strip()]
                    
                    if questions:
                        # Add ALL questions from this category, not just one
                        for question_index, question_text in enumerate(questions):
                            all_questions.append({
                                'category': cat_num,
                                'category_name': category_name,
                                'question': question_text,
                                'original_order': cat_num,
                                'question_index_in_category': question_index,
                                'total_questions_in_category': len(questions),
                                'all_questions': questions  # Keep all for reference
                            })
                        
                        if cat_num not in active_categories:
                            active_categories.append(cat_num)
        
        # If randomization is enabled, shuffle the questions
        if settings['randomize_questions']:
            random.shuffle(all_questions)
        
        settings['active_categories'] = active_categories
        settings['questions'] = all_questions
        settings['total_questions'] = len(all_questions)
        
        return settings
    
    @staticmethod
    def _get_raw_setting(key, default=''):
        """Get raw setting value from database (for PHQ categories that don't use SettingsKey enum)."""
        setting = AppSetting.query.filter_by(key=key).first()
        return setting.value if setting else default
        
    @staticmethod
    def create_phq_session(assessment_session_id, user_id):
        """Create PHQ session data."""
        # Get PHQ settings
        phq_settings = PHQService.get_phq_settings()
        
        # Store questions in session or return for template
        session_data = {
            'questions': phq_settings['questions'],
            'settings': phq_settings,
            'current_question': 0,
            'total_questions': phq_settings['total_questions'],
            'started_at': datetime.utcnow().isoformat()
        }
        
        return session_data
    
    @staticmethod
    def save_phq_response(assessment_session_id, user_id, category_number, response_value, question_text, response_time_ms=None, response_timestamp=None, question_index_in_category=None):
        """Save PHQ response with timing."""
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise Exception("Assessment session not found")
        
        # Check if response already exists for this specific question in category
        existing_response = PHQ9Response.query.filter_by(
            assessment_id=assessment.id,
            question_number=category_number,
            question_index_in_category=question_index_in_category or 0
        ).first()
        
        if existing_response:
            existing_response.response_value = response_value
            existing_response.response_time_ms = response_time_ms
            existing_response.question_text = question_text
            # Update timestamp if provided
            if response_timestamp:
                try:
                    from datetime import datetime
                    existing_response.created_at = datetime.fromtimestamp(int(response_timestamp) / 1000)
                except (ValueError, TypeError):
                    pass  # Keep original timestamp if conversion fails
        else:
            response_data = {
                'assessment_id': assessment.id,
                'question_number': category_number,
                'question_index_in_category': question_index_in_category or 0,
                'question_text': question_text,
                'response_value': response_value,
                'response_time_ms': response_time_ms
            }
            
            # Set timestamp if provided
            if response_timestamp:
                try:
                    from datetime import datetime
                    response_data['created_at'] = datetime.fromtimestamp(int(response_timestamp) / 1000)
                except (ValueError, TypeError):
                    pass  # Use default timestamp if conversion fails
            
            response = PHQ9Response(**response_data)
            db.session.add(response)
        
        db.session.commit()
        return assessment
    
    @staticmethod
    def calculate_phq_score(assessment_session_id, user_id):
        """Calculate PHQ-9 score and save results."""
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise Exception("Assessment session not found")
        
        # Get all responses
        responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
        
        # Group responses by category and calculate category scores
        category_scores = {}
        for response in responses:
            category = response.question_number
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(response.response_value)
        
        # Calculate total score by summing all individual responses
        # (each question contributes its full value regardless of category)
        total_score = sum(response.response_value for response in responses)
        
        # Also calculate average per category if needed for analysis
        category_averages = {
            cat: sum(scores) / len(scores) if scores else 0 
            for cat, scores in category_scores.items()
        }
        
        # Determine severity level
        if total_score >= 20:
            severity = 'severe'
        elif total_score >= 15:
            severity = 'moderately_severe'
        elif total_score >= 10:
            severity = 'moderate'
        elif total_score >= 5:
            severity = 'mild'
        else:
            severity = 'minimal'
        
        # Save score to assessment
        assessment.phq9_score = total_score
        assessment.phq9_severity = severity
        
        # Mark PHQ-9 as completed
        AssessmentService.complete_phq9_assessment(assessment_session_id, user_id)
        
        db.session.commit()
        
        # Prepare results with multi-question support
        results = {
            'total_score': total_score,
            'severity': severity,
            'total_questions': len(responses),
            'total_categories': len(category_scores),
            'category_scores': category_scores,
            'category_averages': category_averages,
            'responses': {f"{r.question_number}_{r.question_index_in_category}": r.response_value for r in responses},
            'response_times': {f"{r.question_number}_{r.question_index_in_category}": r.response_time_ms for r in responses if r.response_time_ms},
            'detailed_responses': [
                {
                    'category': r.question_number,
                    'question_index': r.question_index_in_category,
                    'question_text': r.question_text,
                    'response_value': r.response_value,
                    'response_time_ms': r.response_time_ms,
                    'timestamp': r.created_at.isoformat() if r.created_at else None
                } for r in sorted(responses, key=lambda x: (x.question_number, x.question_index_in_category))
            ],
            'raw_answers': ','.join([str(r.response_value) for r in sorted(responses, key=lambda x: (x.question_number, x.question_index_in_category))])
        }
        
        return results
    
    @staticmethod
    def get_severity_description(severity):
        """Get description for severity level."""
        descriptions = {
            'minimal': 'Minimal depression symptoms',
            'mild': 'Mild depression symptoms',
            'moderate': 'Moderate depression symptoms',
            'moderately_severe': 'Moderately severe depression symptoms',
            'severe': 'Severe depression symptoms'
        }
        return descriptions.get(severity, 'Unknown severity level')