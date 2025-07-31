# app/services/service.py
import jwt
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.user import User
from app.models.patient_profile import PatientProfile

class AuthService:
    @staticmethod
    def authenticate_user(username, password):
        try:
            user = User.query.filter_by(username=username).first()
            
            if not user or not user.check_password(password):
                return None, 'invalid_credentials'
            
            if not user.is_active:
                return user, 'inactive_account'
            
            return user, 'success'
            
        except Exception as e:
            raise e

    @staticmethod
    def register_user(username, email, password, user_type='patient', profile_data=None):
        try:
            # Check existing users
            if User.query.filter_by(username=username).first():
                raise ValueError('Username already exists')
            
            if User.query.filter_by(email=email).first():
                raise ValueError('Email already registered')
            
            # Create user
            user = User(
                username=username,
                email=email,
                user_type=user_type
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            # Create patient profile if needed
            if user_type == 'patient' and profile_data:
                profile = PatientProfile(
                    user_id=user.id,
                    **profile_data
                )
                db.session.add(profile)
            
            db.session.commit()
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def generate_token(user):
        try:
            payload = {
                'user_id': user.id,
                'username': user.username,
                'user_type': user.user_type,
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(
                payload,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            return token
            
        except Exception as e:
            raise e

    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                return None
            
            return user
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            raise e