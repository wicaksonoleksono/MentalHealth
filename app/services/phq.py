# app/services/phq.py
import json
import random
from datetime import datetime
from app import db
from app.models.settings import AppSetting
from app.models.assessment import Assessment, PHQ9Response
from app.services.assesment import AssessmentService


class PHQService:
    @staticmethod
    def get_phq_settings():
        """Load all PHQ settings from database."""
        try:
            settings = {}
            
            # Basic PHQ settings
            settings['instructions'] = PHQService._get_setting('phq9_instructions', '')
            settings['randomize_questions'] = PHQService._get_setting('phq9_randomize_questions', 'false') == 'true'
            settings['show_progress'] = PHQService._get_setting('phq9_show_progress', 'true') == 'true'
            settings['questions_per_page'] = int(PHQService._get_setting('phq9_questions_per_page', '1'))
            
            # Scale settings
            settings['scale_min'] = int(PHQService._get_setting('scale_min', '0'))
            settings['scale_max'] = int(PHQService._get_setting('scale_max', '3'))
            
            # Scale labels
            scale_labels = {}
            for i in range(settings['scale_min'], settings['scale_max'] + 1):
                label = PHQService._get_setting(f'scale_label_{i}', f'Option {i}')
                scale_labels[str(i)] = label
            settings['scale_labels'] = scale_labels
            
            # Get active categories and their questions
            active_categories = []
            all_questions = []
            
            for cat_num in range(1, 10):  # PHQ-9 has 9 categories
                exists = PHQService._get_setting(f'phq_category_{cat_num}_exists', '0')
                if exists == '1':
                    # Get questions for this category
                    questions_json = PHQService._get_setting(f'phq_category_{cat_num}_questions', '[]')
                    try:
                        questions = json.loads(questions_json)
                        if questions:
                            # If multiple questions, randomize within category
                            if len(questions) > 1 and settings['randomize_questions']:
                                selected_question = random.choice(questions)
                            else:
                                selected_question = questions[0]
                            
                            all_questions.append({
                                'category': cat_num,
                                'question': selected_question,
                                'original_order': cat_num
                            })
                            active_categories.append(cat_num)
                    except json.JSONDecodeError:
                        # Fallback: treat as comma-separated
                        questions = [q.strip() for q in questions_json.split(',') if q.strip()]
                        if questions:
                            if len(questions) > 1 and settings['randomize_questions']:
                                selected_question = random.choice(questions)
                            else:
                                selected_question = questions[0]
                            
                            all_questions.append({
                                'category': cat_num,
                                'question': selected_question,
                                'original_order': cat_num
                            })
                            active_categories.append(cat_num)
            
            # Randomize question order if enabled (but keep category tracking)
            if settings['randomize_questions']:
                random.shuffle(all_questions)
            
            settings['active_categories'] = active_categories
            settings['questions'] = all_questions
            settings['total_questions'] = len(all_questions)
            
            return settings
            
        except Exception as e:
            raise e
    
    @staticmethod
    def _get_setting(key, default=''):
        """Helper to get setting value or default."""
        setting = AppSetting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def create_phq_session(assessment_session_id, user_id):
        """Create PHQ session data."""
        try:
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
            
        except Exception as e:
            raise e
    
    @staticmethod
    def save_phq_response(assessment_session_id, user_id, category_number, response_value, question_text, response_time_ms=None):
        """Save PHQ response with timing."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=assessment_session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Check if response already exists for this category
            existing_response = PHQ9Response.query.filter_by(
                assessment_id=assessment.id,
                question_number=category_number
            ).first()
            
            if existing_response:
                existing_response.response_value = response_value
                existing_response.response_time_ms = response_time_ms
            else:
                response = PHQ9Response(
                    assessment_id=assessment.id,
                    question_number=category_number,
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
    def calculate_phq_score(assessment_session_id, user_id):
        """Calculate PHQ-9 score and save results."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=assessment_session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Get all responses
            responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).all()
            
            # Calculate total score
            total_score = sum(response.response_value for response in responses)
            
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
            
            # Prepare results
            results = {
                'total_score': total_score,
                'severity': severity,
                'responses': {r.question_number: r.response_value for r in responses},
                'response_times': {r.question_number: r.response_time_ms for r in responses if r.response_time_ms},
                'raw_answers': ','.join([str(r.response_value) for r in sorted(responses, key=lambda x: x.question_number)])
            }
            
            return results
            
        except Exception as e:
            db.session.rollback()
            raise e
    
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