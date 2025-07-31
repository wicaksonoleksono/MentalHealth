# app/models/assessment.py
from datetime import datetime
from app import db

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(36), nullable=False, unique=True)  # UUID for unique identification
    assessment_type = db.Column(db.String(20), nullable=False)  # 'openquestion', 'phq9', 'photos'
    data_file_path = db.Column(db.String(255))  # JSON file path
    status = db.Column(db.String(20), default='in_progress')
    score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    __table_args__ = (db.Index('idx_user_session', 'user_id', 'session_id'),)
