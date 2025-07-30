# app/services/auth.py

from app.models.user import User
from app import db

class AuthService:
    @staticmethod
    def authenticate_user(username, password):
        """
        Authenticate user.
        Returns user object on success, None on failure.
        Differentiates between invalid credentials and inactive account.
        """
        user = User.query.filter_by(username=username).first()

        # Case 1: User not found or password incorrect
        if not user or not user.check_password(password):
            return None, 'invalid_credentials'

        # Case 2: User account is not active
        if not user.is_active:
            return None, 'inactive_account'

        # Case 3: Success
        return user, 'success'

    @staticmethod
    def register_user(username, email, password, user_type='patient'):
        """Register a new user after validation."""
        if AuthService.check_username_exists(username):
            raise ValueError('Username already exists')
        if AuthService.check_email_exists(email):
            raise ValueError('Email already exists')

        user = User(
            username=username,
            email=email.lower(),
            user_type=user_type
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID."""
        return User.query.get(int(user_id))

    @staticmethod
    def check_username_exists(username):
        """Check if username already exists."""
        return User.query.filter_by(username=username).first() is not None

    @staticmethod
    def check_email_exists(email):
        """Check if email already exists."""
        return User.query.filter_by(email=email.lower()).first() is not None