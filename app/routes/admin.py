# app/routes/admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.decorators.auth import admin_required
from app.services.admin import AdminDashboardService
from app.services.assessment import AssessmentService
from flask import send_file, request, jsonify
from app.services.export import ExportService, ExportException
from app.services.emotion_storage import get_emotion_storage
from datetime import datetime, timedelta
import os
admin_bp = Blueprint('admin', __name__)
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with overview and recent sessions."""
    stats = AdminDashboardService.get_overview_stats()
    recent_sessions = AdminDashboardService.get_recent_sessions(limit=15)
    
    return render_template('admin/dashboard.html', 
                         **stats,
                         recent_sessions=recent_sessions)
# app/routes/admin.py - Add these export routes


@admin_bp.route('/export-session/<session_id>')
@login_required
@admin_required
def export_session(session_id):
    """Export single assessment session data"""
    try:
        # Get user_id from query params or find it
        user_id = request.args.get('user_id')
        if not user_id:
            assessment = Assessment.query.filter_by(session_id=session_id).first()
            if not assessment:
                return jsonify({'error': 'Session not found'}), 404
            user_id = assessment.user_id
        
        # Export the session
        zip_path = ExportService.export_session_data(session_id, user_id)
        
        # Send file and clean up
        def remove_file(response):
            try:
                os.remove(zip_path)
            except:
                pass
            return response
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"assessment_{session_id}.zip",
            mimetype='application/zip'
        )
        
    except ExportException as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@admin_bp.route('/export-bulk', methods=['GET', 'POST'])
@login_required
@admin_required
def export_bulk():
    """Export multiple sessions with filters"""
    if request.method == 'GET':
        # Show export form
        return render_template('admin/export_form.html')
    
    try:
        data = request.get_json() or request.form
        
        # Parse filters
        user_ids = data.get('user_ids')
        if user_ids and isinstance(user_ids, str):
            user_ids = [int(x.strip()) for x in user_ids.split(',') if x.strip()]
        
        # Parse date range
        date_range = None
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include full end day
            date_range = (start_date, end_date)
        
        # Export data
        zip_path = ExportService.export_bulk_data(
            user_ids=user_ids,
            date_range=date_range
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"bulk_assessment_export_{timestamp}.zip",
            mimetype='application/zip'
        )
        
    except ExportException as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Bulk export failed: {str(e)}'}), 500


@admin_bp.route('/export-preview/<session_id>')
@login_required
@admin_required
def export_preview(session_id):
    """Preview what will be exported for a session"""
    try:
        # Get assessment summary
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            return jsonify({'error': 'Session not found'}), 404
        
        summary = AssessmentService.get_assessment_summary(session_id, assessment.user_id)
        
        return jsonify({
            'success': True,
            'preview': summary
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/assessment-data/<session_id>')
@login_required
@admin_required
def view_assessment_data(session_id):
    """View comprehensive assessment data with all settings and responses"""
    try:
        complete_data = AssessmentService.get_complete_assessment_data(session_id)
        if not complete_data:
            flash('Assessment session not found', 'error')
            return redirect(url_for('admin.dashboard'))
        
        return render_template('admin/assessment_detail.html', 
                             assessment_data=complete_data,
                             session_id=session_id)
        
    except Exception as e:
        flash(f'Error loading assessment data: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/assessment-data-api/<session_id>')
@login_required
@admin_required
def get_assessment_data_api(session_id):
    """API endpoint for assessment data (JSON format)"""
    try:
        format_type = request.args.get('format', 'complete')
        
        if format_type == 'summary':
            data = AssessmentService.get_assessment_summary(session_id)
        else:
            data = AssessmentService.get_complete_assessment_data(session_id)
        
        if not data:
            return jsonify({'error': 'Assessment session not found'}), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/storage-management')
@login_required
@admin_required
def storage_management():
    """Storage management dashboard"""
    try:
        stats = get_emotion_storage().get_storage_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/cleanup-storage', methods=['POST'])
@login_required
@admin_required
def cleanup_storage():
    """Clean up old files (admin only)"""
    try:
        result = get_emotion_storage().cleanup_old_files()
        return jsonify({'success': True, 'cleanup_result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# LLM Analysis API Endpoints
@admin_bp.route('/api/llm-analysis/analyze', methods=['POST'])
@login_required
@admin_required
def analyze_session_api():
    """Trigger LLM analysis for a specific session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID is required'}), 400
        
        from app.services.llm_analysis import LLMAnalysisService
        from app.models.assessment import Assessment
        
        # Check if assessment exists
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            return jsonify({'success': False, 'error': 'Assessment not found'}), 404
        
        if assessment.status != 'completed':
            return jsonify({'success': False, 'error': 'Assessment must be completed first'}), 400
        
        # Run analysis
        llm_service = LLMAnalysisService()
        results = llm_service.analyze_session(session_id)
        
        # Count results
        completed = len([r for r in results if r.analysis_status == 'completed'])
        failed = len([r for r in results if r.analysis_status == 'failed'])
        
        return jsonify({
            'success': True,
            'message': 'Analysis completed',
            'completed': completed,
            'failed': failed,
            'total': len(results)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/llm-analysis/results/<session_id>')
@login_required
@admin_required
def get_analysis_results_api(session_id):
    """Get LLM analysis results for a session"""
    try:
        from app.models.llm_analysis import LLMAnalysisResult
        from app.models.assessment import Assessment
        
        # Check if assessment exists
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            return jsonify({'success': False, 'error': 'Assessment not found'}), 404
        
        # Get analysis results
        results = LLMAnalysisResult.query.filter_by(assessment_id=assessment.id).all()
        
        results_data = []
        for result in results:
            result_data = {
                'id': result.id,
                'model_name': result.llm_model.name,
                'provider': result.llm_model.provider,
                'status': result.analysis_status,  # Fixed: use analysis_status
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'processing_time_ms': result.processing_time_ms,
                'error_message': result.error_message,
                'parsed_results': result.get_parsed_results()
            }
            results_data.append(result_data)
        
        return jsonify({
            'success': True,
            'data': results_data,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Model Validation API Endpoint
@admin_bp.route('/api/llm-analysis/validate-model', methods=['POST'])
@login_required
@admin_required
def validate_model_api():
    """Validate an LLM model without saving to database"""
    try:
        data = request.get_json()
        model_name = data.get('model_name', '').strip()
        provider = data.get('provider', 'openai')
        
        if not model_name:
            return jsonify({'success': False, 'error': 'Model name is required'}), 400
        
        from app.services.llm_analysis import LLMAnalysisService
        
        llm_service = LLMAnalysisService()
        validation_result = llm_service.validate_model_without_saving(model_name, provider)
        
        return jsonify({
            'success': validation_result['valid'],
            'error': validation_result['error'],
            'details': validation_result['details'],
            'model_name': model_name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


