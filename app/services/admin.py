# app/services/admin.py
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.assessment import Assessment
from app.models.user import User
class AdminDashboardService:
    @staticmethod
    def get_overview_stats():
        today = datetime.utcnow().date()
        active_sessions = Assessment.query.filter_by(status='in_progress').count()
        total_patients = db.session.query(Assessment.user_id).distinct().count()
        completed_today = Assessment.query.filter(
            Assessment.status == 'completed',
            func.date(Assessment.completed_at) == today
        ).count()
        return {
            'active_sessions': active_sessions,
            'total_patients': total_patients,
            'completed_today': completed_today
        }
    @staticmethod
    def get_recent_sessions(limit=10):
        """Get recent assessment sessions with user info and progress."""
        sessions = db.session.query(Assessment, User).join(
            User, Assessment.user_id == User.id
        ).order_by(Assessment.started_at.desc()).limit(limit).all()
        
        session_data = []
        for assessment, user in sessions:
            completion_info = assessment.get_completion_order()
            
            # Calculate progress
            progress_count = 0
            if completion_info['phq9_completed']:
                progress_count += 1
            if completion_info['open_questions_completed']:
                progress_count += 1
            
            progress_text = f"{progress_count}/2"
            
            # Determine status
            if assessment.status == 'completed':
                status = 'Completed'
                status_class = 'bg-green-100 text-green-800'
            elif assessment.status == 'in_progress':
                status = 'In Progress'
                status_class = 'bg-blue-100 text-blue-800'
            else:
                status = 'Abandoned'
                status_class = 'bg-red-100 text-red-800'
            
            session_data.append({
                'session_id': assessment.session_id,
                'username': user.username,
                'email': user.email,
                'started_at': assessment.started_at,
                'completed_at': assessment.completed_at,
                'first_type': completion_info['first_type'],
                'progress_text': progress_text,
                'progress_count': progress_count,
                'status': status,
                'status_class': status_class,
                'db_status': assessment.status,  # Raw database status
                'phq9_score': assessment.phq9_score,
                'phq9_severity': assessment.phq9_severity,
                'llm_analysis_status': assessment.llm_analysis_status
            })
        
        return session_data