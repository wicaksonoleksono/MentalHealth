# app/services/assessment_balance_service.py  
from app import db
from app.models.assessment import Assessment
from sqlalchemy import func
import random


class AssessmentBalanceService:
    @staticmethod
    def get_next_assessment_order():
        try:
            phq9_first_count = Assessment.query.filter_by(first_assessment_type='phq9').count()
            open_questions_first_count = Assessment.query.filter_by(first_assessment_type='open_questions').count()
            total_assessments = phq9_first_count + open_questions_first_count
            if total_assessments == 0:
                return random.choice(['phq_first', 'questions_first'])
            phq9_ratio = phq9_first_count / total_assessments
            if phq9_ratio > 0.55:  # More than 55% PHQ-9 first
                return 'questions_first'
            elif phq9_ratio < 0.45:  # Less than 45% PHQ-9 first
                return 'phq_first'
            else:
                return random.choice(['phq_first', 'questions_first'])
        except Exception as e:
            return random.choice(['phq_first', 'questions_first'])
    @staticmethod  
    def get_balance_statistics():
        try:
            phq9_first_count = Assessment.query.filter_by(first_assessment_type='phq9').count() 
            open_questions_first_count = Assessment.query.filter_by(first_assessment_type='open_questions').count()
            total_assessments = phq9_first_count + open_questions_first_count
            if total_assessments == 0:
                return {
                    'phq9_first_count': 0,
                    'open_questions_first_count': 0,
                    'total_assessments': 0,
                    'phq9_first_percentage': 50.0,
                    'open_questions_first_percentage': 50.0,
                    'balance_status': 'balanced'
                }
            
            phq9_percentage = (phq9_first_count / total_assessments) * 100
            open_questions_percentage = (open_questions_first_count / total_assessments) * 100
            
            # Determine balance status
            if abs(phq9_percentage - 50) <= 5:  # Within 5% of 50/50
                balance_status = 'balanced'
            elif phq9_percentage > 55:
                balance_status = 'phq9_heavy'
            else:
                balance_status = 'questions_heavy'
            
            return {
                'phq9_first_count': phq9_first_count,
                'open_questions_first_count': open_questions_first_count,
                'total_assessments': total_assessments,
                'phq9_first_percentage': round(phq9_percentage, 1),
                'open_questions_first_percentage': round(open_questions_percentage, 1),
                'balance_status': balance_status
            }
            
        except Exception as e:
            raise e

    @staticmethod
    def assign_assessment_order(session_id, user_id):
        """
        Assign and store the assessment order for a specific session.
        """
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Get the balanced assessment order
            assessment_order = AssessmentBalanceService.get_next_assessment_order()
            
            # Store in assessment (you might want to add this field to the model)
            # For now, we'll store it as a custom field or in session
            # You can add 'assigned_order' field to Assessment model if needed
            
            return assessment_order
            
        except Exception as e:
            raise e