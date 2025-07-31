# app/routes/patient.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import login_required, current_user
from datetime import datetime
import json
from app.decorators.auth import patient_required
from app.models.settings import AppSetting
from app.models.assessment import Assessment
from app.services.assesment import AssessmentService
from app.services.assessment_balance import AssessmentBalanceService
from app.services.phq import PHQService
from app.services.openai_chat import OpenAIChatService

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
    # Create new assessment session
    assessment = AssessmentService.create_assessment_session(current_user.id)
    
    # Store session ID in Flask session
    session['assessment_session_id'] = assessment.session_id
    
    flash('New assessment session started', 'success')
    return redirect(url_for('patient.camera_check'))


@patient_bp.route('/camera-check')
@login_required
@patient_required
def camera_check():
    """Camera permission and functionality check."""
    # Make sure we have an assessment session
    if 'assessment_session_id' not in session:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Get balanced assessment order
    assessment_order = AssessmentBalanceService.get_next_assessment_order()
    session['assessment_order'] = assessment_order  # Store in session
    
    # Progress bar data
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
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        return jsonify({'success': False, 'message': 'No assessment session found'}), 400
    
    # Record camera verification
    AssessmentService.record_camera_verification(assessment_session_id, current_user.id)
    
    return jsonify({
        'success': True,
        'message': 'Camera verified successfully',
        'redirect_url': url_for('patient.consent')
    })


@patient_bp.route('/camera-status', methods=['POST'])
@login_required
@patient_required
def camera_status():
    """Handle camera status updates."""
    data = request.get_json()
    camera_active = data.get('camera_active', False)
    
    return jsonify({
        'success': True,
        'camera_active': camera_active,
        'message': 'Camera status updated'
    })


@patient_bp.route('/consent')
@login_required
@patient_required
def consent():
    """Show consent form with settings from admin."""
    assessment_session_id = session.get('assessment_session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Get consent text from settings
    consent_setting = AppSetting.query.filter_by(key='consent_form_text').first()
    consent_text = consent_setting.value if consent_setting else "Please configure consent form text in admin settings."
    
    # Progress bar data
    progress_data = {
        'current_step_text': 'Step 1 of 4',
        'progress_percentage': 25,
        'assessment_order': assessment_order
    }
    
    return render_template('patient/consent.html', 
                         consent_text=consent_text,
                         session_id=assessment_session_id,
                         **progress_data)


@patient_bp.route('/submit-consent', methods=['POST'])
@login_required
@patient_required
def submit_consent():
    """Process consent form submission and auto-route to first assessment."""
    consent_agreed = request.form.get('consent_agreed')
    session_id = request.form.get('session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not consent_agreed:
        flash('You must agree to the consent form to continue', 'error')
        return redirect(url_for('patient.consent'))
    
    # Record consent
    AssessmentService.record_consent(session_id, current_user.id)
    
    # Auto-route based on assigned balance
    if assessment_order == 'phq_first':
        # Start with PHQ-9
        AssessmentService.start_assessment_type(session_id, current_user.id, 'phq9')
        flash('Starting with PHQ-9 assessment', 'info')
        return redirect(url_for('patient.phq9_assessment'))
    else:
        # Start with Open Questions
        AssessmentService.start_assessment_type(session_id, current_user.id, 'open_questions')
        flash('Starting with open questions', 'info')
        return redirect(url_for('patient.open_questions_assessment'))


@patient_bp.route('/phq9-assessment')
@login_required
@patient_required
def phq9_assessment():
    """PHQ-9 assessment page."""
    assessment_session_id = session.get('assessment_session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Create PHQ session data
    phq_data = PHQService.create_phq_session(assessment_session_id, current_user.id)
    
    # Store PHQ session data
    session['phq_data'] = phq_data
    session['phq_current_question'] = 0
    session['phq_start_time'] = datetime.now().isoformat()
    
    # Progress bar data
    if assessment_order == 'phq_first':
        progress_percentage = 50  # Step 2 of 4
        step_text = 'Step 2 of 4'
    else:
        progress_percentage = 75  # Step 3 of 4  
        step_text = 'Step 3 of 4'
    
    progress_data = {
        'current_step_text': step_text,
        'progress_percentage': progress_percentage,
        'assessment_order': assessment_order
    }
    
    return render_template('patient/phq9_assessment.html', 
                         phq_data=phq_data,
                         session_id=assessment_session_id,
                         **progress_data)


@patient_bp.route('/phq9-question/<int:question_index>')
@login_required
@patient_required
def phq9_question(question_index):
    """Display specific PHQ-9 question."""
    assessment_session_id = session.get('assessment_session_id')
    phq_data = session.get('phq_data')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id or not phq_data:
        flash('PHQ-9 session not found', 'error')
        return redirect(url_for('patient.phq9_assessment'))
    
    if question_index >= len(phq_data['questions']):
        flash('Invalid question index', 'error')
        return redirect(url_for('patient.phq9_assessment'))
    
    # Update current question
    session['phq_current_question'] = question_index
    session['phq_question_start_time'] = datetime.now().isoformat()
    
    # Progress calculation
    if assessment_order == 'phq_first':
        base_progress = 25  # After consent
        question_progress = (question_index / len(phq_data['questions'])) * 25  # 25% for PHQ
        progress_percentage = base_progress + question_progress
        step_text = f'PHQ-9 Question {question_index + 1} of {len(phq_data["questions"])}'
    else:
        base_progress = 50  # After consent + open questions
        question_progress = (question_index / len(phq_data['questions'])) * 25  # 25% for PHQ
        progress_percentage = base_progress + question_progress
        step_text = f'PHQ-9 Question {question_index + 1} of {len(phq_data["questions"])}'
    
    progress_data = {
        'current_step_text': step_text,
        'progress_percentage': progress_percentage,
        'assessment_order': assessment_order
    }
    
    current_question = phq_data['questions'][question_index]
    
    return render_template('patient/phq9_question.html',
                         question=current_question,
                         question_index=question_index,
                         total_questions=len(phq_data['questions']),
                         settings=phq_data['settings'],
                         session_id=assessment_session_id,
                         **progress_data)


@patient_bp.route('/phq9-submit', methods=['POST'])
@login_required
@patient_required
def phq9_submit():
    """Submit PHQ-9 response."""
    assessment_session_id = session.get('assessment_session_id')
    phq_data = session.get('phq_data')
    question_index = int(request.form.get('question_index'))
    response_value = int(request.form.get('response_value'))
    response_time_ms = request.form.get('response_time_ms')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id or not phq_data:
        flash('PHQ-9 session not found', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Calculate response time if provided
    if response_time_ms:
        response_time_ms = int(response_time_ms)
    
    # Get question data
    current_question = phq_data['questions'][question_index]
    category_number = current_question['category']
    question_text = current_question['question']
    
    # Save response
    PHQService.save_phq_response(
        assessment_session_id,
        current_user.id,
        category_number,
        response_value,
        question_text,
        response_time_ms
    )
    
    # Check if this was the last question
    next_question_index = question_index + 1
    if next_question_index >= len(phq_data['questions']):
        # PHQ-9 completed
        results = PHQService.calculate_phq_score(assessment_session_id, current_user.id)
        
        # Check if we need to do the other assessment
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=current_user.id
        ).first()
        
        if assessment and assessment.status == 'completed':
            # Both assessments done
            return redirect(url_for('patient.assessment_complete'))
        else:
            # Need to do open questions
            if assessment_order == 'phq_first':
                flash(f'PHQ-9 completed! Score: {results["total_score"]} ({results["severity"]})', 'success')
                return redirect(url_for('patient.open_questions_assessment'))
            else:
                flash(f'Assessment completed! PHQ-9 Score: {results["total_score"]} ({results["severity"]})', 'success')
                return redirect(url_for('patient.assessment_complete'))
    else:
        # Go to next question
        return redirect(url_for('patient.phq9_question', question_index=next_question_index))


@patient_bp.route('/open-questions-assessment')
@login_required
@patient_required
def open_questions_assessment():
    """Open questions assessment page with AI chat."""
    assessment_session_id = session.get('assessment_session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Initialize chat service
    chat_service = OpenAIChatService()
    chat_session = chat_service.create_chat_session(assessment_session_id, current_user.id)
    
    # Store chat session
    session['chat_session'] = chat_session
    
    # Progress bar data
    if assessment_order == 'phq_first':
        progress_percentage = 75  # Step 3 of 4
        step_text = 'Step 3 of 4'
    else:
        progress_percentage = 50  # Step 2 of 4  
        step_text = 'Step 2 of 4'
    
    progress_data = {
        'current_step_text': step_text,
        'progress_percentage': progress_percentage,
        'assessment_order': assessment_order
    }
    
    return render_template('patient/open_questions_assessment.html', 
                         chat_settings=chat_session['settings'],
                         session_id=assessment_session_id,
                         **progress_data)


@patient_bp.route('/chat-message', methods=['POST'])
@login_required
@patient_required
def chat_message():
    """Handle chat message with streaming response."""
    data = request.get_json()
    user_message = data.get('message')
    assessment_session_id = session.get('assessment_session_id')
    chat_session = session.get('chat_session')
    
    if not assessment_session_id or not chat_session or not user_message:
        return jsonify({'error': 'Invalid request'}), 400
    
    # Initialize chat service
    chat_service = OpenAIChatService()
    
    # Check if chat should continue
    can_continue, end_message = chat_service.should_continue_chat(chat_session)
    if not can_continue:
        return jsonify({
            'response': end_message,
            'should_end': True,
            'redirect_url': url_for('patient.complete_open_questions')
        })
    
    # Generate response (non-streaming for now, we'll add streaming route separately)
    response_chunks = []
    start_time = datetime.now()
    
    for chunk in chat_service.generate_streaming_response(chat_session, user_message):
        response_chunks.append(chunk)
    
    full_response = ''.join(response_chunks)
    response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # Save chat exchange
    chat_service.save_chat_exchange(
        assessment_session_id,
        current_user.id,
        user_message,
        full_response,
        response_time_ms
    )
    
    # Update session
    session['chat_session'] = chat_session
    
    return jsonify({
        'response': full_response,
        'should_end': False,
        'exchange_count': chat_session['exchange_count']
    })


@patient_bp.route('/chat-stream', methods=['POST'])
@login_required
@patient_required
def chat_stream():
    """Stream chat response in real-time."""
    data = request.get_json()
    user_message = data.get('message')
    assessment_session_id = session.get('assessment_session_id')
    chat_session = session.get('chat_session')
    
    if not assessment_session_id or not chat_session or not user_message:
        return jsonify({'error': 'Invalid request'}), 400
    
    def generate():
        chat_service = OpenAIChatService()
        
        # Check if chat should continue
        can_continue, end_message = chat_service.should_continue_chat(chat_session)
        if not can_continue:
            yield f"data: {json.dumps({'type': 'end', 'message': end_message})}\n\n"
            return
        
        # Stream response
        full_response = ""
        for chunk in chat_service.generate_streaming_response(chat_session, user_message):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # Save exchange
        chat_service.save_chat_exchange(
            assessment_session_id,
            current_user.id,
            user_message,
            full_response
        )
        
        # Update session
        session['chat_session'] = chat_session
        
        yield f"data: {json.dumps({'type': 'complete', 'exchange_count': chat_session['exchange_count']})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@patient_bp.route('/complete-open-questions', methods=['GET', 'POST'])
@login_required
@patient_required
def complete_open_questions():
    """Complete open questions assessment."""
    assessment_session_id = session.get('assessment_session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Mark open questions as completed
    AssessmentService.complete_open_questions_assessment(assessment_session_id, current_user.id)
    
    # Check if we need to do PHQ-9
    assessment = Assessment.query.filter_by(
        session_id=assessment_session_id,
        user_id=current_user.id
    ).first()
    
    if assessment and assessment.status == 'completed':
        # Both assessments done
        flash('All assessments completed successfully!', 'success')
        return redirect(url_for('patient.assessment_complete'))
    else:
        # Need to do PHQ-9
        if assessment_order == 'questions_first':
            flash('Open questions completed! Now starting PHQ-9 assessment.', 'success')
            return redirect(url_for('patient.phq9_assessment'))
        else:
            flash('Assessment completed!', 'success')
            return redirect(url_for('patient.assessment_complete'))


@patient_bp.route('/debug-session')
@login_required
@patient_required
def debug_session():
    """Debug route to check session and services."""
    debug_info = {
        'session_data': {
            'assessment_session_id': session.get('assessment_session_id'),
            'assessment_order': session.get('assessment_order'),
            'user_id': current_user.id,
            'username': current_user.username
        }
    }
    
    # Test PHQ Service
    try:
        phq_settings = PHQService.get_phq_settings()
        debug_info['phq_service'] = {
            'status': 'working',
            'total_questions': phq_settings.get('total_questions', 0),
            'active_categories': phq_settings.get('active_categories', [])
        }
    except Exception as e:
        debug_info['phq_service'] = {'status': 'error', 'error': str(e)}
    
    # Test Chat Service
    try:
        chat_service = OpenAIChatService()
        chat_settings = chat_service.get_chat_settings()
        debug_info['chat_service'] = {
            'status': 'working',
            'has_preprompt': bool(chat_settings.get('preprompt')),
            'max_exchanges': chat_settings.get('max_exchanges')
        }
    except Exception as e:
        debug_info['chat_service'] = {'status': 'error', 'error': str(e)}
    
    return jsonify(debug_info)


@patient_bp.route('/assessment-complete')
@login_required
@patient_required
def assessment_complete():
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    session.pop('assessment_session_id', None)
    return render_template('patient/assessment_complete.html')