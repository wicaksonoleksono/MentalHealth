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
    
    # Ensure instance directory exists
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)
    try:
        assessment_dirs = [
            'exports'
            ,'uploads'
        ]
        for dir_name in assessment_dirs:
            os.makedirs(os.path.join(upload_folder, dir_name), exist_ok=True)
        
        print(f"Upload directories initialized at: {upload_folder}")
    except Exception as e:
        print(f"Warning: Could not initialize upload directories: {e}")
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        # Import here to avoid circular imports
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp  
    from app.routes.patient import patient_bp
    from app.routes.admin import admin_bp
    from app.routes.settings import settings_bp
    from app.routes.admin_llm_analysis import admin_llm_analysis_bp
    
    # Register blueprints with prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(admin_llm_analysis_bp)
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)
    
    return app