# app/routes/settings.py - Updated with section routing

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.decorators.auth import admin_required
from app.services.settings import SettingsService, SettingsException
from app.models.settings import AppSetting

settings_bp = Blueprint('settings', __name__)

# Valid sections
VALID_SECTIONS = ['openquestion', 'consent', 'phq9', 'recording']

@settings_bp.route('/admin/settings/')
@login_required
@admin_required
def show_settings():
    """Redirect to default section"""
    return redirect(url_for('settings.show_settings_section', section='openquestion'))

@settings_bp.route('/admin/settings/<section>')
@login_required
@admin_required
def show_settings_section(section):
    """Show specific settings section"""
    if section not in VALID_SECTIONS:
        flash(f'Invalid settings section: {section}', 'error')
        return redirect(url_for('settings.show_settings_section', section='openquestion'))
    
    try:
        # Get all settings for the template
        settings_data = SettingsService.get_all()
        
        # Flatten for template compatibility
        flattened = {}
        for category, settings in settings_data.items():
            flattened.update(settings)
        
        # Add PHQ category data
        from app.models.assessment import PHQCategoryType
        flattened['phq_category_types'] = PHQCategoryType.get_all_data()
        
        # Get existing PHQ categories from database (check 1-20 range)
        existing_categories = []
        phq_categories = {}
        
        for cat_num in range(1, 21):  # Support up to 20 categories
            exists_key = f'phq_category_{cat_num}_exists'
            exists_setting = AppSetting.query.filter_by(key=exists_key).first()
            if exists_setting and exists_setting.value == '1':
                existing_categories.append(cat_num)
                
                # Get category name
                name_key = f'phq_category_{cat_num}_name'
                name_setting = AppSetting.query.filter_by(key=name_key).first()
                category_name = name_setting.value if name_setting else f'Category {cat_num}'
                
                # Get questions
                questions_key = f'phq_category_{cat_num}_questions'
                questions_setting = AppSetting.query.filter_by(key=questions_key).first()
                try:
                    import json
                    questions = json.loads(questions_setting.value) if questions_setting and questions_setting.value else []
                except:
                    questions = []
                
                phq_categories[cat_num] = {
                    'questions': questions,
                    'name': category_name
                }
                
                # Add to flattened data for template access
                flattened[exists_key] = '1'
                flattened[name_key] = category_name
                flattened[questions_key] = questions  # Pass parsed list directly
        
        flattened['existing_categories'] = existing_categories
        flattened['existing_category_numbers'] = existing_categories
        flattened['phq_categories'] = phq_categories
        
        return render_template('admin/settings.html',
                             active_section=section,
                             settings_data=flattened,
                             categorized_settings=settings_data)
                             
    except SettingsException as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@settings_bp.route('/admin/settings/<section>', methods=['POST'])
@login_required
@admin_required
def save_settings_section(section):
    """Save settings for specific section"""
    if section not in VALID_SECTIONS:
        flash(f'Invalid settings section: {section}', 'error')
        return redirect(url_for('settings.show_settings_section', section='openquestion'))
    
    try:
        form_data = dict(request.form)
        updated_count = SettingsService.update_bulk(form_data)
        flash(f'Settings saved successfully! Updated {updated_count} settings.', 'success')
        
    except SettingsException as e:
        flash(f'Error saving settings: {str(e)}', 'error')
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
    
    return redirect(url_for('settings.show_settings_section', section=section))
@settings_bp.route('/api/settings/recording/config')
@login_required  
def api_recording_config():
    try:
        config = SettingsService.get_recording_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/settings/phq9/config')
@login_required
def api_phq9_config():
    try:
        config = SettingsService.get_phq9_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/settings/openquestion/config')
@login_required
def api_openquestion_config():
    try:
        text_settings = SettingsService.get_group(SettingsKey.get_text_settings)
        config = {
            'prompt': text_settings.get('openquestion_prompt', ''),
            'instructions': text_settings.get('openquestion_instructions', '')
        }
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/settings/consent/config')
@login_required
def api_consent_config():
    try:
        text_settings = SettingsService.get_group(SettingsKey.get_text_settings)
        config = {
            'text': text_settings.get('consent_form_text', '')
        }
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/settings/<section>/reset', methods=['POST'])
@login_required
@admin_required
def api_reset_section(section):
    try:
        if section not in VALID_SECTIONS:
            return jsonify({'success': False, 'error': 'Invalid section'}), 400
        
        reset_count = 0
        if section == 'recording':
            for setting_key in SettingsKey.get_recording_settings():
                if setting_key.default is not None:
                    SettingsService.set(setting_key, setting_key.default)
                    reset_count += 1
        elif section == 'phq9':
            for setting_key in SettingsKey.get_phq9_settings():
                if setting_key.default is not None:
                    SettingsService.set(setting_key, setting_key.default)
                    reset_count += 1
        elif section in ['openquestion', 'consent']:
            for setting_key in SettingsKey.get_text_settings():
                if setting_key.default is not None:
                    SettingsService.set(setting_key, setting_key.default)
                    reset_count += 1
        
        return jsonify({'success': True, 'reset_count': reset_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500