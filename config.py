import os

# Get the absolute path of the directory the config.py file is in.
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secure_default_secret_key")
    
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session config
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # CSRF Protection (disabled for development)
    WTF_CSRF_ENABLED = False
    
    # Upload config (for photos later)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    