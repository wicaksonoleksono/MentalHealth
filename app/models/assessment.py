# app/models/assessment.py
from datetime import datetime
from app import db

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(36), nullable=False)  # UUID for grouping
    assessment_type = db.Column(db.String(20), nullable=False)  # 'openquestion', 'phq9', 'photos'
    data_file_path = db.Column(db.String(255))  # /storage/assessments/{session_id}/openquestion.json
    status = db.Column(db.String(20), default='in_progress')  # 'completed', 'abandoned'
    score = db.Column(db.Float)  # PHQ-9 score, sentiment score, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)