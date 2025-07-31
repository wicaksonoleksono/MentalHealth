# app/controllers/settings.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required
from app.decorators.auth import admin_required
from app.services.settings import SettingsService, SettingsException

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/admin/settings', methods=['GET'])
@login_required
@admin_required
def show_settings():
    try:
        settings_data = SettingsService.get_all_settings()
        phq_data = SettingsService.get_phq_management_data()
        
        return render_template('admin/settings.html',
                             active_tab=request.args.get('tab', 'openquestion'),
                             **settings_data,
                             **phq_data)
    except SettingsException as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@settings_bp.route('/admin/settings', methods=['POST'])
@login_required  
@admin_required
def save_settings():
    """Handle all form-based settings including PHQ settings"""
    active_tab = request.form.get('active_tab', 'openquestion')
    
    try:
        form_data = {
            # Core settings
            'openquestion_prompt': request.form.get('openquestion_prompt', '').strip(),
            'consent_form_text': request.form.get('consent_form_text', '').strip(),
            'openquestion_instructions': request.form.get('openquestion_instructions', '').strip(),
            'phq9_instructions': request.form.get('phq9_instructions', '').strip(),
            
            # Image capture settings
            'capture_interval': request.form.get('capture_interval', '5'),
            'image_quality': request.form.get('image_quality', '0.8'),
            'image_resolution': request.form.get('image_resolution', '1280x720'),
            'enable_capture': 'true' if request.form.get('enable_capture') else 'false',
            
            # PHQ scale settings
            'scale_min': request.form.get('scale_min', '0'),
            'scale_max': request.form.get('scale_max', '3'),
            
            # PHQ additional settings
            'phq9_randomize_questions': 'true' if request.form.get('phq9_randomize_questions') else 'false',
            'phq9_show_progress': 'true' if request.form.get('phq9_show_progress') else 'false',
            'phq9_questions_per_page': request.form.get('phq9_questions_per_page', '1'),
        }
        
        # Add dynamic scale labels
        scale_min = int(request.form.get('scale_min', 0))
        scale_max = int(request.form.get('scale_max', 3))
        
        for i in range(scale_min, scale_max + 1):
            label_key = f'scale_label_{i}'
            label_value = request.form.get(label_key)
            if label_value:
                form_data[label_key] = label_value.strip()
        
        SettingsService.update_settings(form_data)
        flash('Settings saved successfully!', 'success')
        
    except SettingsException as e:
        flash(f'Error saving settings: {str(e)}', 'error')
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'error')
    except Exception as e:
        flash('An unexpected error occurred while saving settings', 'error')
    
    return redirect(url_for('settings.show_settings', tab=active_tab))
@settings_bp.route('/debug/flash')
@login_required
@admin_required
def debug_flash():
    """Debug route to test flash messages"""
    flash('Test success message!', 'success')
    flash('Test error message!', 'error')
    return redirect(url_for('settings.show_settings'))