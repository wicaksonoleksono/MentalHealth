import os

# Get the absolute path of the directory the config.py file is in.
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secure_default_secret_key")
    
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'webm', 'mp4', 'mov'}
    DEFAULT_IMAGE_QUALITY = 0.8
    DEFAULT_VIDEO_QUALITY = '720p'
    DEFAULT_CAPTURE_INTERVAL = 5  # seconds
    DEFAULT_RESOLUTION = '1280x720'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')