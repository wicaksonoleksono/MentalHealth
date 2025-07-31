# app/decorators/auth.py
from functools import wraps
from flask import request, jsonify, abort
from flask_login import current_user
from app.services.auth import AuthService


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superuser():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_superuser():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'message': 'No token provided'}), 401
            
            if token.startswith('Bearer '):
                token = token[7:]
            
            user = AuthService.verify_token(token)
            if not user:
                return jsonify({'message': 'Invalid or expired token'}), 401
            
            # Add user to request context
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'message': 'Token verification failed'}), 500
    
    return decorated_function


def jwt_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'message': 'No token provided'}), 401
            
            if token.startswith('Bearer '):
                token = token[7:]
            
            user = AuthService.verify_token(token)
            if not user or not user.is_superuser():
                return jsonify({'message': 'Admin access required'}), 403
            
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'message': 'Token verification failed'}), 500
    
    return decorated_function


def jwt_patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'message': 'No token provided'}), 401
            
            if token.startswith('Bearer '):
                token = token[7:]
            
            user = AuthService.verify_token(token)
            if not user or not user.is_patient():
                return jsonify({'message': 'Patient access required'}), 403
            
            request.current_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'message': 'Token verification failed'}), 500
    
    return decorated_function