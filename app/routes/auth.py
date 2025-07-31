# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_user, logout_user, current_user
from app.services.auth import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        if request.form:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                return jsonify({'errors': {'general': 'Username and password are required.'}}), 422

            try:
                user, status = AuthService.authenticate_user(username.strip(), password)

                if status == 'success':
                    login_user(user)
                    token = AuthService.generate_token(user)
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Login successful',
                        'token': token,
                        'user_type': user.user_type
                    }), 200
                    
                elif status == 'inactive_account':
                    return jsonify({'message': 'Your account has been disabled. Please contact support.'}), 403
                else:
                    return jsonify({'message': 'Invalid username or password. Please check your credentials and try again.'}), 401

            except Exception as e:
                return jsonify({'message': 'An internal server error occurred. Please try again later.'}), 500

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or len(username.strip()) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template('auth/register.html')
            
        if not email or '@' not in email:
            flash('Please enter a valid email', 'error')
            return render_template('auth/register.html')
            
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        try:
            # Collect profile data
            profile_data = {
                'age': int(request.form.get('age')) if request.form.get('age') else None,
                'gender': request.form.get('gender') or None,
                'educational_level': request.form.get('educational_level') or None,
                'cultural_background': request.form.get('cultural_background') or None,
                'medical_conditions': request.form.get('medical_conditions') or None,
                'medications': request.form.get('medications') or None,
                'emergency_contact': request.form.get('emergency_contact') or None
            }
            
            # Always create patient accounts with profile
            user = AuthService.register_user(
                username.strip(),
                email.strip().lower(),
                password,
                'patient',
                profile_data
            )
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html')
            
        except Exception as e:
            flash('Registration failed due to a server error.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'No token provided'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        user = AuthService.verify_token(token)
        if not user:
            return jsonify({'message': 'Invalid or expired token'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'user_type': user.user_type
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Token verification failed'}), 500