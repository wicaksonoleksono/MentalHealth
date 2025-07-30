# app/controllers/patient.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.decorators.auth import patient_required

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    return render_template('patient/dashboard.html')

@patient_bp.route('/assessment')
@login_required
@patient_required
def assessment():
    # Will handle the full assessment flow later
    return render_template('patient/assessment.html')