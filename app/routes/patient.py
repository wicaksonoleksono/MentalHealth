# app/routes/patient.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app.decorators.auth import patient_required
from app.models.settings import AppSetting
from app.services.assesment import AssessmentService
from app.services.assessment_balance import AssessmentBalanceService

patient_bp = Blueprint('patient', __name__)


@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    """Patient dashboard - entry point for assessments."""
    return render_template('patient/dashboard.html')


@patient_bp.route('/start-assessment')
@login_required
@patient_required
def start_assessment():
    """Start a new assessment session."""
    try:
        assessment = AssessmentService.create_assessment_session(current_user.id)
        session['assessment_session_id'] = assessment.session_id
        flash('New assessment session started', 'success')
        return redirect(url_for('patient.camera_check'))
    except Exception as e:
        print(f"Error starting assessment: {e}")  # Debug
        flash('Error starting assessment session', 'error')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/camera-check')
@login_required
@patient_required
def camera_check():
    """Camera permission and functionality check."""
    if 'assessment_session_id' not in session:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    assessment_order = AssessmentBalanceService.get_next_assessment_order()
    session['assessment_order'] = assessment_order  # Store in session
    progress_data = {
        'current_step_text': 'Camera Check',
        'progress_percentage': 12.5,
        'assessment_order': assessment_order
    }
    return render_template('patient/camera_check.html', **progress_data)


@patient_bp.route('/camera-verified', methods=['POST'])
@login_required
@patient_required
def camera_verified():
    """Record camera verification."""
    try:
        assessment_session_id = session.get('assessment_session_id')
        if not assessment_session_id:
            return jsonify({'success': False, 'message': 'No assessment session found'}), 400
        AssessmentService.record_camera_verification(assessment_session_id, current_user.id)
        return jsonify({
            'success': True,
            'message': 'Camera verified successfully',
            'redirect_url': url_for('patient.consent')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to verify camera'}), 500


@patient_bp.route('/camera-status', methods=['POST'])
@login_required
@patient_required
def camera_status():
    """Handle camera status updates."""
    try:
        data = request.get_json()
        camera_active = data.get('camera_active', False)
        return jsonify({
            'success': True,
            'camera_active': camera_active,
            'message': 'Camera status updated'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Failed to update camera status'
        }), 500


@patient_bp.route('/consent')
@login_required
@patient_required
def consent():
    """Show consent form with settings from admin."""
    try:
        assessment_session_id = session.get('assessment_session_id')
        assessment_order = session.get('assessment_order', 'phq_first')
        if not assessment_session_id:
            flash('Please start a new assessment session', 'error')
            return redirect(url_for('patient.dashboard'))
        consent_setting = AppSetting.query.filter_by(key='consent_form_text').first()
        consent_text = consent_setting.value if consent_setting else "Please configure consent form text in admin settings."
        progress_data = {
            'current_step_text': 'Step 1 of 4',
            'progress_percentage': 25,
            'assessment_order': assessment_order
        }
        return render_template('patient/consent.html', 
                             consent_text=consent_text,
                             session_id=assessment_session_id,
                             **progress_data)
    except Exception as e:
        flash('Error loading consent form', 'error')
        return redirect(url_for('patient.dashboard'))


@patient_bp.route('/submit-consent', methods=['POST'])
@login_required
@patient_required
def submit_consent():
    """Process consent form submission and auto-route to first assessment."""
    try:
        consent_agreed = request.form.get('consent_agreed')
        session_id = request.form.get('session_id')
        assessment_order = session.get('assessment_order', 'phq_first')
        if not consent_agreed:
            flash('You must agree to the consent form to continue', 'error')
            return redirect(url_for('patient.consent'))
        AssessmentService.record_consent(session_id, current_user.id)
        if assessment_order == 'phq_first':
            AssessmentService.start_assessment_type(session_id, current_user.id, 'phq9')
            flash('Starting with PHQ-9 assessment', 'info')
            return redirect(url_for('patient.phq9_assessment'))
        else:
            AssessmentService.start_assessment_type(session_id, current_user.id, 'open_questions')
            flash('Starting with open questions', 'info')
            return redirect(url_for('patient.open_questions_assessment'))
    except Exception as e:
        flash('Error processing consent', 'error')
        return redirect(url_for('patient.consent'))


@patient_bp.route('/choose-assessment')
@login_required
@patient_required
def choose_assessment():
    """Let patient choose which assessment to start with."""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/choose_assessment.html', session_id=assessment_session_id)


@patient_bp.route('/start-phq9')
@login_required
@patient_required
def start_phq9():
    """Start PHQ-9 assessment."""
    try:
        assessment_session_id = session.get('assessment_session_id')
        if not assessment_session_id:
            flash('Please start a new assessment session', 'error')
            return redirect(url_for('patient.dashboard'))
        AssessmentService.start_assessment_type(assessment_session_id, current_user.id, 'phq9')
        return redirect(url_for('patient.phq9_assessment'))
    except Exception as e:
        flash('Error starting PHQ-9 assessment', 'error')
        return redirect(url_for('patient.choose_assessment'))


@patient_bp.route('/start-open-questions')
@login_required
@patient_required
def start_open_questions():
    """Start open questions assessment."""
    try:
        assessment_session_id = session.get('assessment_session_id')
        if not assessment_session_id:
            flash('Please start a new assessment session', 'error')
            return redirect(url_for('patient.dashboard'))
        AssessmentService.start_assessment_type(assessment_session_id, current_user.id, 'open_questions')
        return redirect(url_for('patient.open_questions_assessment'))
    except Exception as e:
        flash('Error starting open questions assessment', 'error')
        return redirect(url_for('patient.choose_assessment'))


@patient_bp.route('/phq9-assessment')
@login_required
@patient_required
def phq9_assessment():
    """PHQ-9 assessment page."""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/phq9_assessment.html', session_id=assessment_session_id)


@patient_bp.route('/open-questions-assessment')
@login_required
@patient_required
def open_questions_assessment():
    """Open questions assessment page."""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/open_questions_assessment.html', session_id=assessment_session_id)


@patient_bp.route('/assessment-complete')
@login_required
@patient_required
def assessment_complete():
    """Assessment completion page."""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Clear session
    session.pop('assessment_session_id', None)
    
    return render_template('patient/assessment_complete.html')