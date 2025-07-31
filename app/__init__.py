# app/__init__.py 
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from config import Config
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ensure instance directory exists for SQLite
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    from app.services.auth import AuthService


    @login_manager.user_loader
    def load_user(user_id):
        return AuthService.get_user_by_id(user_id)
    from app.controllers.auth import auth_bp
    from app.controllers.main import main_bp  
    from app.controllers.patient import patient_bp
    from app.controllers.admin import admin_bp
    from app.controllers.phq import phq_bp
    from app.controllers.settings import settings_bp
    app.register_blueprint(settings_bp,url_prefix="/settings")
    app.register_blueprint(phq_bp, url_prefix='/phq')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    from app.cli import register_commands
    register_commands(app)
    
    return app