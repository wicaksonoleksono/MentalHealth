# app/routes/aspy
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import login_required, current_user
from flask import current_app
from datetime import datetime
import json
import base64
from app import db
from app.decorators.auth import patient_required
from app.models.settings import AppSetting
from app.models.assessment import Assessment, EmotionData
from app.services.assesment import AssessmentService
from app.services.assessment_balance import AssessmentBalanceService
from app.services.phq import PHQService
from app.services.openai_chat import OpenAIChatService
from app.services.emotion_storage import emotion_storage
from app.services.settings import SettingsService
patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    """Dashboard with incomplete assessment detection."""
    # Check for incomplete assessments
    incomplete_assessment = Assessment.query.filter_by(
        user_id=current_user.id,
        status='in_progress'
    ).order_by(Assessment.started_at.desc()).first()
    
    incomplete_data = None
    if incomplete_assessment:
        incomplete_data = {
            'session_id': incomplete_assessment.session_id,
            'started_at': incomplete_assessment.started_at,
            'camera_verified': incomplete_assessment.camera_verified,
            'consent_agreed': incomplete_assessment.consent_agreed,
            'phq9_completed': incomplete_assessment.phq9_completed,
            'open_questions_completed': incomplete_assessment.open_questions_completed,
            'first_assessment_type': incomplete_assessment.first_assessment_type
        }
    
    return render_template('patient/dashboard.html', incomplete_assessment=incomplete_data)


@patient_bp.route('/discard-incomplete', methods=['POST'])
@login_required
@patient_required
def discard_incomplete():
    """Discard incomplete assessment and allow new one."""
    # Mark any incomplete assessments as abandoned
    incomplete_assessments = Assessment.query.filter_by(
        user_id=current_user.id,
        status='in_progress'
    ).all()
    
    for assessment in incomplete_assessments:
        assessment.status = 'abandoned'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Incomplete assessment discarded'
    })

@patient_bp.route('/start-assessment')
@login_required
@patient_required
def start_assessment():
    """Start a new assessment session - check for incomplete assessments first."""
    # Check for incomplete assessments first
    incomplete_assessment = Assessment.query.filter_by(
        user_id=current_user.id,
        status='in_progress'
    ).order_by(Assessment.started_at.desc()).first()
    
    if incomplete_assessment:
        # Show modal with completion status
        completion_status = {
            'has_incomplete': True,
            'session_id': incomplete_assessment.session_id,
            'consent_done': incomplete_assessment.consent_agreed,
            'camera_done': incomplete_assessment.camera_verified,
            'phq9_done': incomplete_assessment.phq9_completed,
            'open_questions_done': incomplete_assessment.open_questions_completed,
            'started_at': incomplete_assessment.started_at.strftime('%B %d, %Y at %I:%M %p')
        }
        
        return render_template('patient/resume_assessment_modal.html', 
                             completion_status=completion_status)
    
    # No incomplete assessment, start fresh
    assessment = AssessmentService.create_assessment_session(current_user.id)
    session['assessment_session_id'] = assessment.session_id
    flash('New assessment session started', 'success')
    return redirect(url_for('patient.camera_check'))


@patient_bp.route('/start-fresh-assessment', methods=['POST'])
@login_required
@patient_required
def start_fresh_assessment():
    """Start a completely fresh assessment, discarding any incomplete ones."""
    discard_session_id = request.form.get('discard_session_id')
    
    # Mark the old assessment as abandoned
    if discard_session_id:
        old_assessment = Assessment.query.filter_by(
            session_id=discard_session_id,
            user_id=current_user.id,
            status='in_progress'
        ).first()
        
        if old_assessment:
            old_assessment.status = 'abandoned'
            
            # Clean up any media files associated with the old assessment
            try:
                # Clean up files for discarded session
                emotion_storage.cleanup_session_files(discard_session_id, current_user.id)
            except Exception as e:
                current_app.logger.warning(f"Failed to cleanup media files for session {discard_session_id}: {e}")
            
            db.session.commit()
    
    # Start completely fresh assessment
    assessment = AssessmentService.create_assessment_session(current_user.id)
    session['assessment_session_id'] = assessment.session_id
    
    # Clear any existing session data
    session.pop('phq_data', None)
    session.pop('chat_session', None) 
    session.pop('assessment_order', None)
    session.modified = True
    
    flash('Previous assessment discarded. Starting fresh assessment session.', 'success')
    return redirect(url_for('patient.camera_check'))


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
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        return jsonify({'success': False, 'message': 'No assessment session found'}), 400
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
    AssessmentService.record_consent(session_id, current_user.id)
    if assessment_order == 'phq_first':
        AssessmentService.start_assessment_type(session_id, current_user.id, 'phq9')
        flash('Starting with PHQ-9 assessment', 'info')
        return redirect(url_for('patient.phq9_assessment'))
    else:
        AssessmentService.start_assessment_type(session_id, current_user.id, 'open_questions')
        flash('Starting with open questions', 'info')
        return redirect(url_for('patient.open_questions_assessment'))
# app/routes/patient.py - PHQ-9 section fixes

@patient_bp.route('/phq9-assessment')
@login_required
@patient_required
def phq9_assessment():
    """PHQ-9 assessment page - redirects to first question."""
    assessment_session_id = session.get('assessment_session_id')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    try:
        # Create PHQ session data
        phq_data = PHQService.create_phq_session(assessment_session_id, current_user.id)
        
        # Check if there are any questions available
        if not phq_data.get('questions') or len(phq_data['questions']) == 0:
            flash('No PHQ-9 questions are configured. Please contact an administrator to set up the assessment.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        # Get and save assessment settings for consistency
        recording_config = SettingsService.get_recording_config()
        assessment_order = session.get('assessment_order', 'phq_first')
        
        # Save settings to assessment record
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=current_user.id
        ).first()
        
        if assessment:
            assessment.set_phq9_settings(phq_data['settings'])
            assessment.set_recording_settings(recording_config)
            assessment.assessment_order = assessment_order
            db.session.commit()
        
        # Store PHQ session data
        session['phq_data'] = phq_data
        session['phq_start_time'] = datetime.now().isoformat()
        
        # Start with first assessment type
        AssessmentService.start_assessment_type(assessment_session_id, current_user.id, 'phq9')
        
        # Redirect to first question
        return redirect(url_for('patient.phq9_question', question_index=0))
        
    except Exception as e:
        flash(f'Error setting up PHQ-9 assessment: {str(e)}', 'error')
        return redirect(url_for('patient.dashboard'))


@patient_bp.route('/phq9-question/<int:question_index>')
@login_required
@patient_required
def phq9_question(question_index):
    assessment_session_id = session.get('assessment_session_id')
    phq_data = session.get('phq_data')
    assessment_order = session.get('assessment_order', 'phq_first')
    
    # Check if assessment session exists
    if not assessment_session_id:
        flash('Please start a new assessment session', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Check if PHQ data exists, if not try to create it
    if not phq_data:
        try:
            phq_data = PHQService.create_phq_session(assessment_session_id, current_user.id)
            session['phq_data'] = phq_data
            session['phq_start_time'] = datetime.now().isoformat()
        except Exception as e:
            flash(f'Error setting up PHQ-9 assessment: {str(e)}', 'error')
            return redirect(url_for('patient.dashboard'))
    
    # Check if there are any questions available
    if not phq_data.get('questions') or len(phq_data['questions']) == 0:
        flash('No PHQ-9 questions are configured. Please contact an administrator.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Validate question index
    if question_index >= len(phq_data['questions']):
        flash(f'Invalid question index {question_index}. Redirecting to first question.', 'warning')
        return redirect(url_for('patient.phq9_question', question_index=0))
    session['phq_current_question'] = question_index
    session['phq_question_start_time'] = datetime.now().isoformat()
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
    
    # Get recording settings for camera capture
    recording_config = SettingsService.get_recording_config()
    
    return render_template('patient/phq9_question.html',
                         question=current_question,
                         question_index=question_index,
                         total_questions=len(phq_data['questions']),
                         settings=phq_data['settings'],
                         recording_config=recording_config,
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
    response_timestamp = request.form.get('response_timestamp')
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
    question_index_in_category = current_question.get('question_index_in_category', 0)
    
    # Save response with timestamp and question index
    PHQService.save_phq_response(
        assessment_session_id,
        current_user.id,
        category_number,
        response_value,
        question_text,
        response_time_ms,
        response_timestamp,
        question_index_in_category
    )
    next_question_index = question_index + 1
    if next_question_index >= len(phq_data['questions']):
        results = PHQService.calculate_phq_score(assessment_session_id, current_user.id)
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=current_user.id
        ).first()
        if assessment and assessment.status == 'completed':
            flash(f'Assessment completed! PHQ-9 Score: {results["total_score"]} ({results["severity"]})', 'success')
            return redirect(url_for('patient.assessment_complete'))
        else:
            if assessment_order == 'phq_first':
                flash(f'PHQ-9 completed! Score: {results["total_score"]} ({results["severity"]})', 'success')
                return redirect(url_for('patient.open_questions_assessment'))
            else:
                flash(f'Assessment completed! PHQ-9 Score: {results["total_score"]} ({results["severity"]})', 'success')
                return redirect(url_for('patient.assessment_complete'))
    else:
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
    
    # Create chat session and get settings
    chat_service = OpenAIChatService()
    chat_session = chat_service.create_chat_session(assessment_session_id, current_user.id)
    session['chat_session'] = chat_session
    
    # Get recording settings for consistency
    recording_config = SettingsService.get_recording_config()
    
    # Save chat and recording settings to assessment record
    assessment = Assessment.query.filter_by(
        session_id=assessment_session_id,
        user_id=current_user.id
    ).first()
    
    if assessment:
        assessment.set_chat_settings(chat_session['settings'])
        # Update recording settings if not already set
        if not assessment.recording_settings:
            assessment.set_recording_settings(recording_config)
        if not assessment.assessment_order:
            assessment.assessment_order = assessment_order
        db.session.commit()
    if assessment_order == 'phq_first':
        progress_percentage = 75
        step_text = 'Step 3 of 4'
    else:
        progress_percentage = 50
        step_text = 'Step 2 of 4'
    progress_data = {
        'current_step_text': step_text,
        'progress_percentage': progress_percentage,
        'assessment_order': assessment_order
    }
    # Get recording settings for camera capture
    recording_config = SettingsService.get_recording_config()
    
    return render_template('patient/open_questions_assessment.html', 
                         chat_settings=chat_session['settings'],
                         recording_config=recording_config,
                         session_id=assessment_session_id,
                         **progress_data)

@patient_bp.route('/test-chat', methods=['GET'])
@login_required
@patient_required
def test_chat():
    """Test route to check if OpenAI service is working"""
    try:
        from app.services.openai_chat import OpenAIChatService
        chat_service = OpenAIChatService()
        
        # Test settings
        settings = chat_service.get_chat_settings()
        
        # Test chat session creation
        test_session = chat_service.create_chat_session("test-session", current_user.id)
        
        return jsonify({
            'success': True,
            'settings_loaded': bool(settings.get('openquestion_prompt')),
            'session_created': bool(test_session.get('system_prompt')),
            'system_prompt_length': len(test_session.get('system_prompt', '')),
            'message': 'OpenAI service is working correctly'
        })
        
    except Exception as e:
        current_app.logger.error(f"Test chat error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'OpenAI service test failed'
        }), 500

@patient_bp.route('/chat-stream/<message>')
@login_required
@patient_required
def chat_stream(message):
    assessment_session_id = session.get('assessment_session_id')
    chat_session = session.get('chat_session')
    
    if not assessment_session_id or not chat_session or not message:
        return Response("data: " + json.dumps({'type': 'error', 'message': 'Invalid request'}) + "\n\n",
                       mimetype='text/event-stream')
    
    # Pre-add user message to both histories
    current_time = datetime.utcnow().isoformat()
    chat_session['message_history'].append({'type': 'human', 'content': message})
    chat_session['conversation_history'].append({
        'type': 'human', 
        'content': message,
        'timestamp': current_time
    })
    
    def generate():
        response_content = ""
        chat_service = OpenAIChatService()
        
        for chunk in chat_service.generate_streaming_response(chat_session, message):
            response_content += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # Add AI response to both histories and update count
        chat_session['message_history'].append({'type': 'ai', 'content': response_content})
        chat_session['conversation_history'].append({
            'type': 'ai', 
            'content': response_content,
            'timestamp': datetime.utcnow().isoformat()
        })
        chat_session['exchange_count'] = chat_session.get('exchange_count', 0) + 1
        
        yield f"data: {json.dumps({'type': 'complete', 'exchange_count': chat_session['exchange_count']})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@patient_bp.route('/update-chat-session', methods=['POST'])
@login_required  
@patient_required
def update_chat_session():
    """Update chat session after streaming completes - called from frontend."""
    assessment_session_id = session.get('assessment_session_id')
    chat_session = session.get('chat_session')
    
    if not assessment_session_id or not chat_session:
        return jsonify({'success': False, 'message': 'No chat session found'}), 400
    
    # Just save the current chat session back to Flask session
    session['chat_session'] = chat_session
    session.modified = True
    
    return jsonify({
        'success': True,
        'exchange_count': chat_session.get('exchange_count', 0),
        'message_count': len(chat_session.get('message_history', []))
    })



@patient_bp.route('/save-conversation', methods=['POST'])
@login_required
@patient_required
def save_conversation():
    """Save the complete conversation when user is done."""
    assessment_session_id = session.get('assessment_session_id')
    chat_session = session.get('chat_session')
    
    if not assessment_session_id or not chat_session:
        return jsonify({'success': False, 'message': 'No conversation to save'}), 400
    
    try:
        # Log conversation summary before saving
        current_app.logger.info(f"Saving conversation for session {assessment_session_id}, "
                               f"exchanges: {chat_session.get('exchange_count', 0)}, "
                               f"messages: {len(chat_session.get('message_history', []))}")
        
        chat_service = OpenAIChatService()
        saved_assessment = chat_service.save_conversation(
            assessment_session_id,
            current_user.id,
            chat_session
        )
        
        # Mark assessment as having open questions completed
        AssessmentService.start_assessment_type(assessment_session_id, current_user.id, 'open_questions')
        
        # Clear chat session from Flask session
        session.pop('chat_session', None)
        session.modified = True
        
        current_app.logger.info(f"Successfully saved conversation for session {assessment_session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Conversation saved successfully',
            'exchanges_saved': chat_session.get('exchange_count', 0),
            'assessment_id': saved_assessment.id
        })
    
    except Exception as e:
        current_app.logger.error(f"Failed to save conversation for session {assessment_session_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to save conversation: {str(e)}'
        }), 500


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

@patient_bp.route('/assessment-complete')
@login_required
@patient_required
def assessment_complete():
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        flash('No assessment session found', 'error')
        return redirect(url_for('patient.dashboard'))
    assessment = Assessment.query.filter_by(
        session_id=assessment_session_id,
        user_id=current_user.id
    ).first()
    if not assessment or assessment.status != 'completed':
        flash('Assessment not completed', 'error')
        return redirect(url_for('patient.dashboard'))
    session.pop('assessment_session_id', None)
    session.pop('phq_data', None)
    session.pop('chat_session', None)
    session.pop('assessment_order', None)
    session.modified = True
    completion_data = {
        'completion_time': assessment.completed_at,
        'phq9_score': assessment.phq9_score,
        'phq9_severity': assessment.phq9_severity
    }

    return render_template('patient/assessment_complete.html', **completion_data)

@patient_bp.route('/capture-emotion-binary', methods=['POST'])
@login_required
@patient_required
def capture_emotion_binary():
    """Handle binary file uploads (unified service)"""
    try:
        
        # Validate session
        assessment_session_id = session.get('assessment_session_id')
        if not assessment_session_id:
            return jsonify({'success': False, 'message': 'No assessment session found'}), 400
        
        # Get file from request
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Get form data
        assessment_type = request.form.get('assessment_type')
        question_identifier = request.form.get('question_identifier')
        media_type = request.form.get('media_type')
        
        if not all([assessment_type, question_identifier, media_type]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Read file data
        file_data = file.read()
        
        # Prepare metadata
        metadata = {
            'duration_ms': int(request.form.get('duration_ms', 0)),
            'capture_timestamp': int(request.form.get('capture_timestamp', 0)),
            'conversation_elapsed_ms': int(request.form.get('conversation_elapsed_ms', 0))
        }
        
        # Parse recording settings if provided
        recording_settings = request.form.get('recording_settings')
        if recording_settings:
            try:
                import json
                metadata['recording_settings'] = json.loads(recording_settings)
            except:
                pass
        
        # Save using unified emotion storage service (VPS + Database in one call!)
        if media_type == 'video':
            emotion_data = emotion_storage.save_video(
                session_id=assessment_session_id,
                user_id=current_user.id,
                assessment_type=assessment_type,
                question_identifier=question_identifier,
                video_data=file_data,
                filename=file.filename,
                metadata=metadata
            )
        elif media_type == 'image':
            emotion_data = emotion_storage.save_image(
                session_id=assessment_session_id,
                user_id=current_user.id,
                assessment_type=assessment_type,
                question_identifier=question_identifier,
                image_data=file_data,
                filename=file.filename,
                metadata=metadata
            )
        else:
            return jsonify({'success': False, 'message': 'Invalid media type'}), 400
        
        return jsonify({
            'success': True,
            'file_path': emotion_data.file_path,
            'file_size': emotion_data.file_size,
            'database_id': emotion_data.id,
            'message': f'{media_type.title()} saved successfully'
        })
        
    except Exception as e:
        print(f"Emotion capture error: {e}")
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500


@patient_bp.route('/storage-stats')
@login_required
@patient_required 
def get_storage_stats():
    """Get storage statistics"""
    try:
        stats = emotion_storage.get_storage_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@patient_bp.route('/my-files')
@login_required
@patient_required
def get_my_files():
    """Get files for current user"""
    try:
        session_id = session.get('assessment_session_id')
        files = emotion_storage.get_user_files(current_user.id, session_id)
        return jsonify({'success': True, 'files': files, 'total': len(files)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@patient_bp.route('/session-files')
@login_required
@patient_required
def get_session_files():
    """Get all captured files for current session"""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        return jsonify({'success': False, 'message': 'No assessment session found'}), 400
    
    try:
        # Get files using unified service
        files = emotion_storage.get_session_files(assessment_session_id, current_user.id)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_files': len(files),
            'total_size': sum(f['file_size'] for f in files if f['file_size'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@patient_bp.route('/validate-session-files')
@login_required
@patient_required
def validate_session_files():
    """Validate that all database records have corresponding files"""
    assessment_session_id = session.get('assessment_session_id')
    if not assessment_session_id:
        return jsonify({'success': False, 'message': 'No assessment session found'}), 400
    
    try:
        # Validate files using unified service
        validation_result = emotion_storage.validate_session_files(assessment_session_id, current_user.id)
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Optional: Route to serve captured files (for testing/preview)
@patient_bp.route('/emotion-file/<int:emotion_id>')
@login_required
@patient_required
def serve_emotion_file(emotion_id):
    """Serve captured emotion file"""
    from flask import send_file
    
    # Get emotion data record
    emotion_data = EmotionData.query.filter_by(id=emotion_id).first()
    if not emotion_data:
        return jsonify({'error': 'File not found'}), 404
    
    # Verify user owns this file
    assessment = Assessment.query.filter_by(
        id=emotion_data.assessment_id,
        user_id=current_user.id
    ).first()
    
    if not assessment:
        return jsonify({'error': 'Access denied'}), 403
    
    # Check if file exists
    if not emotion_data.file_exists():
        return jsonify({'error': 'Physical file not found'}), 404
    
    try:
        return send_file(
            emotion_data.get_full_path(),
            mimetype=emotion_data.mime_type,
            as_attachment=False
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# # Patient routes for their own data
# @patient_bp.route('/export-my-session/<session_id>')
# @login_required
# @patient_required
# def export_my_session(session_id):
#     """Allow patients to export their own session data"""
#     try:
#         assessment = Assessment.query.filter_by(
#             session_id=session_id,
#             user_id=current_user.id
#         ).first()
#         if not assessment:
#             return jsonify({'error': 'Session not found or access denied'}), 404
#         # Export the session
#         zip_path = ExportService.export_session_data(session_id, current_user.id)
#         # 
#         return send_file(
#             zip_path,
#             as_attachment=True,
#             download_name=f"my_assessment_{session_id}.zip",
#             mimetype='application/zip'
#         )
#         # 
#     except ExportException as e:
#         return jsonify({'error': str(e)}), 400
#     except Exception as e:
#         return jsonify({'error': f'Export failed: {str(e)}'}), 500