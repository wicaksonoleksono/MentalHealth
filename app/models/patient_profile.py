from datetime import datetime
from app import db
class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    # Demographic info - patient-specific only
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))  # 'male', 'female', 'other', 'prefer_not_to_say'
    educational_level = db.Column(db.String(50))  # 'high_school', 'bachelor', 'master', 'phd'
    cultural_background = db.Column(db.String(100))
    medical_conditions = db.Column(db.Text)
    medications = db.Column(db.Text)
    emergency_contact = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    def __repr__(self):
        return f'<PatientProfile for User {self.user_id}>'