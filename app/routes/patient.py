# app/routes/patient.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.decorators.auth import patient_required
from app.services.assessment import AssessmentService, AssessmentException
from app.services.settings import SettingsService
import uuid

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    return render_template('patient/dashboard.html')

@patient_bp.route('/assessment/camera-check')
@login_required
@patient_required
def camera_check():
    """Camera permission check before starting assessment"""
    try:
        # Get image capture settings for display
        settings = SettingsService.get_all_settings()
        
        return render_template('patient/camera_check.html', 
                             capture_interval=settings.get('capture_interval', 5),
                             image_quality=settings.get('image_quality', 0.8),
                             image_resolution=settings.get('image_resolution', '1280x720'),
                             enable_capture=settings.get('enable_capture', True))
    except Exception as e:
        flash(f'Error loading camera check: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/assessment/start')
@login_required
@patient_required
def start_assessment():
    """Start new assessment - show consent form"""
    try:
        # Generate session ID for this assessment
        session_id = str(uuid.uuid4())
        session['assessment_session_id'] = session_id
        
        # Get consent form text from settings
        settings = SettingsService.get_all_settings()
        consent_text = settings.get('consent_form_text', '')
        
        return render_template('patient/consent.html', 
                             session_id=session_id,
                             consent_text=consent_text)
    except Exception as e:
        flash(f'Error starting assessment: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/assessment/consent', methods=['POST'])
@login_required
@patient_required
def submit_consent():
    """Handle consent form submission"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            flash('Session expired. Please start again.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        # Check if user agreed to consent
        consent_agreed = request.form.get('consent_agreed') == 'on'
        if not consent_agreed:
            flash('You must agree to the consent form to proceed.', 'error')
            return redirect(url_for('patient.start_assessment'))
        
        # Create assessment record
        AssessmentService.create_assessment_session(
            user_id=current_user.id,
            session_id=session_id
        )
        
        # Store consent in session
        session['consent_given'] = True
        
        # Redirect to next step
        return redirect(url_for('patient.open_questions'))
        
    except AssessmentException as e:
        flash(f'Error processing consent: {str(e)}', 'error')
        return redirect(url_for('patient.start_assessment'))

@patient_bp.route('/assessment/open-questions')
@login_required
@patient_required
def open_questions():
    """Open question phase with AI assistant"""
    if not session.get('consent_given'):
        flash('Please complete consent form first.', 'error')
        return redirect(url_for('patient.start_assessment'))
    
    try:
        session_id = session.get('assessment_session_id')
        settings = SettingsService.get_all_settings()
        
        return render_template('patient/open_questions.html',
                             session_id=session_id,
                             openquestion_prompt=settings.get('openquestion_prompt', ''),
                             image_settings=AssessmentService.get_image_capture_settings())
    except Exception as e:
        flash(f'Error loading open questions: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/assessment/phq9')
@login_required
@patient_required
def phq9_questions():
    """PHQ-9 questionnaire phase"""
    if not session.get('consent_given'):
        flash('Please complete consent form first.', 'error')
        return redirect(url_for('patient.start_assessment'))
    
    try:
        session_id = session.get('assessment_session_id')
        questions = AssessmentService.get_randomized_phq_questions()
        
        return render_template('patient/phq9.html',
                             session_id=session_id,
                             questions=questions)
    except Exception as e:
        flash(f'Error loading PHQ-9: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/assessment/complete')
@login_required
@patient_required
def complete_assessment():
    """Assessment completion page"""
    try:
        session_id = session.get('assessment_session_id')
        if session_id:
            AssessmentService.complete_assessment(session_id)
            # Clear session data
            session.pop('assessment_session_id', None)
            session.pop('consent_given', None)
        
        return render_template('patient/complete.html')
    except Exception as e:
        flash(f'Error completing assessment: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))