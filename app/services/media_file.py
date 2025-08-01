# app/services/media_file.py

import os
import uuid
from datetime import datetime
from flask import current_app
from app import db
from app.models.assessment import Assessment, EmotionData

class MediaFileException(Exception):
    pass

class MediaFileService:
    
    @staticmethod
    def _get_upload_root():
        """Get the base upload directory"""
        return current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    @staticmethod
    def _ensure_directory(path):
        """Create directory if it doesn't exist"""
        os.makedirs(path, exist_ok=True)
    
    @staticmethod
    def _get_session_directory(session_id, assessment_type, media_type):
        """Generate organized directory path for session files"""
        # Structure: assessments/{session_id}/camera/{media_type}s/{assessment_type}/
        relative_path = os.path.join(
            'assessments',
            session_id,
            'camera',
            f"{media_type}s",  # 'images' or 'videos'
            assessment_type
        )
        return relative_path
    
    @staticmethod
    def save_emotion_capture(session_id, user_id, assessment_type, question_identifier, 
                           file_data, media_type, original_filename=None, metadata=None):
        """Save emotion capture file and create database record"""
        
        # Validate assessment exists
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise MediaFileException(f"Assessment session not found: {session_id}")
        
        # Generate file info
        file_extension = MediaFileService._get_file_extension(media_type, original_filename)
        filename = f"{question_identifier}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        # Get directory paths
        relative_dir = MediaFileService._get_session_directory(session_id, assessment_type, media_type)
        full_dir = os.path.join(MediaFileService._get_upload_root(), relative_dir)
        
        # Create directory
        MediaFileService._ensure_directory(full_dir)
        
        # Full file paths
        full_file_path = os.path.join(full_dir, filename)
        relative_file_path = os.path.join(relative_dir, filename)
        
        # Save file
        with open(full_file_path, 'wb') as f:
            f.write(file_data)
        
        # Get file info
        file_size = len(file_data)
        mime_type = MediaFileService._get_mime_type(media_type, file_extension)
        
        # Create database record
        emotion_data = EmotionData(
            assessment_id=assessment.id,
            assessment_type=assessment_type,
            question_identifier=question_identifier,
            media_type=media_type,
            file_path=relative_file_path,
            original_filename=original_filename or filename,
            file_size=file_size,
            mime_type=mime_type,
            resolution=metadata.get('resolution') if metadata else None,
            quality_setting=metadata.get('quality') if metadata else None,
            duration_ms=metadata.get('duration_ms') if metadata else None
        )
        
        db.session.add(emotion_data)
        db.session.commit()
        
        return emotion_data
    
    @staticmethod
    def get_session_files(session_id, user_id=None):
        """Get all files for a session"""
        query = db.session.query(EmotionData, Assessment).join(
            Assessment, EmotionData.assessment_id == Assessment.id
        ).filter(Assessment.session_id == session_id)
        
        if user_id:
            query = query.filter(Assessment.user_id == user_id)
        
        results = query.all()
        
        files = []
        for emotion_data, assessment in results:
            files.append({
                'id': emotion_data.id,
                'media_type': emotion_data.media_type,
                'assessment_type': emotion_data.assessment_type,
                'question_identifier': emotion_data.question_identifier,
                'file_path': emotion_data.file_path,
                'full_path': emotion_data.get_full_path(),
                'file_size': emotion_data.file_size,
                'exists': emotion_data.file_exists(),
                'timestamp': emotion_data.timestamp
            })
        
        return files
    
    @staticmethod
    def cleanup_session_files(session_id, user_id=None):
        """Remove all files for a session"""
        files = MediaFileService.get_session_files(session_id, user_id)
        
        deleted_count = 0
        for file_info in files:
            if file_info['exists']:
                os.remove(file_info['full_path'])
                deleted_count += 1
        
        # Remove empty directories
        session_dir = os.path.join(
            MediaFileService._get_upload_root(),
            'assessments',
            session_id
        )
        
        if os.path.exists(session_dir):
            # Remove empty subdirectories
            for root, dirs, files in os.walk(session_dir, topdown=False):
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    if not os.listdir(dir_path):  # Empty directory
                        os.rmdir(dir_path)
            
            # Remove session directory if empty
            if not os.listdir(session_dir):
                os.rmdir(session_dir)
        
        return deleted_count
    
    @staticmethod
    def validate_session_files(session_id, user_id=None):
        """Check if all database records have corresponding files"""
        files = MediaFileService.get_session_files(session_id, user_id)
        
        missing_files = [f for f in files if not f['exists']]
        total_files = len(files)
        valid_files = total_files - len(missing_files)
        
        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'missing_files': len(missing_files),
            'missing_file_details': missing_files,
            'is_valid': len(missing_files) == 0
        }
    
    @staticmethod
    def _get_file_extension(media_type, original_filename=None):
        """Get appropriate file extension"""
        if original_filename and '.' in original_filename:
            return '.' + original_filename.split('.')[-1].lower()
        
        # Default extensions
        defaults = {
            'image': '.jpg',
            'video': '.webm'
        }
        return defaults.get(media_type, '.bin')
    
    @staticmethod
    def _get_mime_type(media_type, file_extension):
        """Get MIME type based on media type and extension"""
        mime_map = {
            'image': {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp'
            },
            'video': {
                '.webm': 'video/webm',
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime'
            }
        }
        return mime_map.get(media_type, {}).get(file_extension.lower(), 'application/octet-stream')