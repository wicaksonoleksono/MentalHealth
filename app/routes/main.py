# app/controllers/main.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    if current_user.is_superuser():
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('patient.dashboard'))
@main_bp.route('/welcome')
@login_required  
def welcome():
    return render_template('index.html')