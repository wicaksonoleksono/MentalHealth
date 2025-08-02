# app/routes/admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.decorators.auth import admin_required
from app.services.admin import AdminDashboardService
from app.services.assessment_data import AssessmentDataService
from flask import send_file, request, jsonify
from app.services.export import ExportService, ExportException
from app.services.emotion_storage import emotion_storage
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
        complete_data = AssessmentDataService.get_complete_assessment_data(session_id)
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
            data = AssessmentDataService.get_assessment_summary(session_id)
        else:
            data = AssessmentDataService.get_complete_assessment_data(session_id)
        
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
        stats = emotion_storage.get_storage_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/cleanup-storage', methods=['POST'])
@login_required
@admin_required
def cleanup_storage():
    """Clean up old files (admin only)"""
    try:
        result = emotion_storage.cleanup_old_files()
        return jsonify({'success': True, 'cleanup_result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


