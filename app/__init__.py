# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import os
from flask_login import login_required, current_user
from flask import render_template, redirect, url_for

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name=None):
    app = Flask(__name__)
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    # Get config object and apply to app
    config_obj = config.get(config_name, config['default'])
    app.config.from_object(config_obj)
    
    # Use config object's basedir for instance path
    from config import basedir
    instance_path = os.path.join(basedir, 'instance')
    
    # Check if instance directory exists, if not ask for confirmation
    if not os.path.exists(instance_path):
        if click.confirm(f'Instance directory does not exist at {instance_path}. Create it?'):
            os.makedirs(instance_path, exist_ok=True)
            print(f"✅ Created instance directory: {instance_path}")
        else:
            print(f"❌ Skipped creating instance directory")
    
    # Create upload and export directories using config values
    upload_folder = app.config['UPLOAD_FOLDER']
    exports_folder = app.config.get('EXPORTS_FOLDER', os.path.join(basedir, 'exports'))
    
    # Check and create upload folder
    if not os.path.exists(upload_folder):
        if click.confirm(f'Upload directory does not exist at {upload_folder}. Create it?'):
            os.makedirs(upload_folder, exist_ok=True)
            print(f"✅ Created upload directory: {upload_folder}")
        else:
            print(f"❌ Skipped creating upload directory")
    
    # Check and create exports folder  
    if not os.path.exists(exports_folder):
        if click.confirm(f'Exports directory does not exist at {exports_folder}. Create it?'):
            os.makedirs(exports_folder, exist_ok=True)
            print(f"✅ Created exports directory: {exports_folder}")
        else:
            print(f"❌ Skipped creating exports directory")
    
    print(f"Directories status:")
    print(f"  Instance: {instance_path} ({'✅' if os.path.exists(instance_path) else '❌'})")
    print(f"  Uploads: {upload_folder} ({'✅' if os.path.exists(upload_folder) else '❌'})")
    print(f"  Exports: {exports_folder} ({'✅' if os.path.exists(exports_folder) else '❌'})")

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

    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')

    @app.before_request
    def before_request():
        from flask import request
        if not current_user.is_authenticated and request.endpoint not in ['auth.login', 'auth.register', 'static']:
            return redirect(url_for('auth.login'))
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
