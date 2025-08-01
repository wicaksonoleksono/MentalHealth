# app/services/user_service.py
from app import db
from app.models.user import User
from app.models.patient_profile import PatientProfile
class UserService:
    @staticmethod
    def create_patient(username, email, password, profile_data=None):
        try:
            user = User(
                username=username,
                email=email,
                user_type='patient'
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()  # Get user.id
            
            # Create patient profile if data provided
            if profile_data:
                profile = PatientProfile(
                    user_id=user.id,
                    age=profile_data.get('age'),
                    gender=profile_data.get('gender'),
                    educational_level=profile_data.get('educational_level'),
                    cultural_background=profile_data.get('cultural_background'),
                    medical_conditions=profile_data.get('medical_conditions'),
                    medications=profile_data.get('medications'),
                    emergency_contact=profile_data.get('emergency_contact')
                )
                db.session.add(profile)
            
            db.session.commit()
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def create_superuser(username, email, password):
        try:
            user = User(
                username=username,
                email=email,
                user_type='superuser'
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_patient_profile(user_id, profile_data):
        try:
            user = User.query.get(user_id)
            if not user or not user.is_patient():
                raise ValueError("Invalid patient user")
            
            if not user.patient_profile:
                profile = PatientProfile(user_id=user_id)
                db.session.add(profile)
            else:
                profile = user.patient_profile
            
            # Update fields
            for field in ['age', 'gender', 'educational_level', 'cultural_background', 
                         'medical_conditions', 'medications', 'emergency_contact']:
                if field in profile_data:
                    setattr(profile, field, profile_data[field])
            
            db.session.commit()
            return profile
            
        except Exception as e:
            db.session.rollback()
            raise e