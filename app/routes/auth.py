# app/routes/auth.py (or modal/auth.py)

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user
from app.services.auth import AuthService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Assuming 'index' is your main page route name
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
                    # The frontend handles the redirect, but we confirm success.
                    return jsonify({'success': True, 'message': 'Login successful'}), 200
                elif status == 'inactive_account':
                    # 403 Forbidden - Your frontend is already looking for this
                    return jsonify({'message': 'Your account has been disabled. Please contact support.'}), 403
                else: # 'invalid_credentials'
                    # 401 Unauthorized - Your frontend is looking for this
                    return jsonify({'message': 'Invalid username or password. Please check your credentials and try again.'}), 401

            except Exception as e:
                print(f"Login error: {e}")  # For debugging
                return jsonify({'message': 'An internal server error occurred. Please try again later.'}), 500

    # For GET requests or non-AJAX POSTs
    return render_template('auth/login.html')

# The /register and /logout routes are now correct with the service-level changes.
# No changes are needed for them.

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            user_type = request.form.get('user_type', 'patient')
            errors = {}
            
            # Basic validation
            if not username or len(username.strip()) < 3: errors['username'] = 'Username must be at least 3 characters'
            if not email or '@' not in email: errors['email'] = 'Please enter a valid email'
            if not password or len(password) < 6: errors['password'] = 'Password must be at least 6 characters'
            if password != confirm_password: errors['confirm_password'] = 'Passwords do not match'
            
            if errors:
                return jsonify({'errors': errors}), 422
            
            try:
                user = AuthService.register_user(
                    username.strip(), 
                    email.strip().lower(), 
                    password, 
                    user_type
                )
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Redirecting to login...',
                }), 201
                
            except ValueError as e: # This now works because the service raises the error
                error_message = str(e).lower()
                if 'username' in error_message:
                    return jsonify({'errors': {'username': 'This username is already taken.'}}), 409
                elif 'email' in error_message:
                    return jsonify({'errors': {'email': 'This email is already registered.'}}), 409
                else:
                    return jsonify({'message': str(e)}), 400
                    
            except Exception as e:
                print(f"Registration error: {e}")
                return jsonify({'message': 'Registration failed due to a server error.'}), 500
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))