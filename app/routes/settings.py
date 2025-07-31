# app/routes/settings.py
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
        return render_template('admin/settings.html',
                            active_tab=request.args.get('tab', 'openquestion'),
                            **settings_data)
    except SettingsException as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@settings_bp.route('/admin/settings', methods=['POST'])
@login_required
@admin_required
def save_settings():
    try:
        active_tab = request.form.get('active_tab', 'openquestion')
        form_data = dict(request.form)
        print(f"Raw form data: {form_data}")
        SettingsService.update_settings(form_data)
        flash('Settings saved successfully!', 'success')
    except SettingsException as e:
        flash(f'Error saving settings: {str(e)}', 'error')
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
    
    return redirect(url_for('settings.show_settings', tab=active_tab))