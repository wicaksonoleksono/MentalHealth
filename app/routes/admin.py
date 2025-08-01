# app/routes/admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.decorators.auth import admin_required
from app.services.admin import AdminDashboardService

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
