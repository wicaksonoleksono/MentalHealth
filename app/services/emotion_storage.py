"""
Unified Emotion Storage Service
Handles both VPS file storage AND database records in one clean service
Replaces the messy media_file.py + vps_storage.py combination
"""
import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from PIL import Image
import logging

from app import db
from app.models.assessment import Assessment, EmotionData

logger = logging.getLogger(__name__)

class EmotionStorageService:
    """Unified service for emotion capture: VPS storage + database records"""
    
    def __init__(self, base_dir: str = "./uploads"):
        self.base_dir = Path(base_dir)
        self.max_storage_gb = 10
        self.retention_days = 30
        self.max_file_size_mb = 50
        self.image_quality = 85
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_storage_path(self, user_id: int, session_id: str, assessment_type: str) -> Path:
        """Generate organized storage path"""
        date_path = datetime.now().strftime('%Y/%m/%d')
        return self.base_dir / date_path / f"user_{user_id}" / assessment_type / f"session_{session_id}"
    
    def save_video(self, session_id: str, user_id: int, assessment_type: str, 
                   question_identifier: str, video_data: bytes, filename: str, 
                   metadata: Dict) -> EmotionData:
        """Save video to VPS storage AND create database record"""
        try:
            # Validate file size
            file_size_mb = len(video_data) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                raise ValueError(f"File too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB")
            
            # Get assessment
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            if not assessment:
                raise ValueError(f"Assessment not found: {session_id}")
            
            # Create VPS storage path
            storage_path = self.get_storage_path(user_id, session_id, assessment_type)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"video_{timestamp}.webm"
            file_path = storage_path / safe_filename
            
            # Save file to VPS
            with open(file_path, 'wb') as f:
                f.write(video_data)
            
            # Get relative path for database
            relative_path = str(file_path.relative_to(self.base_dir))
            
            # Create database record with standardized timestamps
            now = datetime.utcnow()
            captured_at = now  # Default to now if no timestamp provided
            
            # Parse capture timestamp if provided
            if metadata.get('capture_timestamp'):
                try:
                    captured_at = datetime.fromtimestamp(int(metadata['capture_timestamp']) / 1000)
                except (ValueError, TypeError):
                    pass  # Use default
            
            emotion_data = EmotionData(
                assessment_id=assessment.id,
                assessment_type=assessment_type,
                question_identifier=question_identifier,
                media_type='video',
                file_path=relative_path,
                original_filename=filename,
                file_size=len(video_data),
                mime_type='video/webm',
                # STANDARDIZED TIMESTAMPS
                created_at=now,  # When saved to database
                captured_at=captured_at,  # When user actually captured
                question_started_at=self._parse_question_start_time(metadata),
                # TECHNICAL METADATA
                duration_ms=metadata.get('duration_ms'),
                time_into_question_ms=metadata.get('conversation_elapsed_ms'),
                recording_settings=str(metadata.get('recording_settings', {}))
            )
            
            db.session.add(emotion_data)
            db.session.commit()
            
            logger.info(f"Video saved: {relative_path} ({file_size_mb:.1f}MB)")
            return emotion_data
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save video: {e}")
            raise
    
    def save_image(self, session_id: str, user_id: int, assessment_type: str,
                   question_identifier: str, image_data: bytes, filename: str, 
                   metadata: Dict) -> EmotionData:
        """Save image to VPS storage AND create database record"""
        try:
            # Get assessment
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            if not assessment:
                raise ValueError(f"Assessment not found: {session_id}")
            
            # Create storage path
            storage_path = self.get_storage_path(user_id, session_id, assessment_type)
            images_path = storage_path / "images"
            images_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            safe_filename = f"capture_{timestamp}.jpg"
            file_path = images_path / safe_filename
            
            # Save and optimize image
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Optimize with PIL
            try:
                with Image.open(file_path) as img:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.save(file_path, 'JPEG', optimize=True, quality=self.image_quality)
                optimized_size = file_path.stat().st_size
            except Exception as e:
                logger.warning(f"Image optimization failed: {e}")
                optimized_size = len(image_data)
            
            # Get relative path for database
            relative_path = str(file_path.relative_to(self.base_dir))
            
            # Create database record with standardized timestamps
            now = datetime.utcnow()
            captured_at = now  # Default to now if no timestamp provided
            
            # Parse capture timestamp if provided
            if metadata.get('capture_timestamp'):
                try:
                    captured_at = datetime.fromtimestamp(int(metadata['capture_timestamp']) / 1000)
                except (ValueError, TypeError):
                    pass  # Use default
            
            emotion_data = EmotionData(
                assessment_id=assessment.id,
                assessment_type=assessment_type,
                question_identifier=question_identifier,
                media_type='image',
                file_path=relative_path,
                original_filename=filename,
                file_size=optimized_size,
                mime_type='image/jpeg',
                # STANDARDIZED TIMESTAMPS
                created_at=now,  # When saved to database
                captured_at=captured_at,  # When user actually captured
                question_started_at=self._parse_question_start_time(metadata),
                # TECHNICAL METADATA
                time_into_question_ms=metadata.get('conversation_elapsed_ms'),
                recording_settings=str(metadata.get('recording_settings', {}))
            )
            
            db.session.add(emotion_data)
            db.session.commit()
            
            logger.info(f"Image saved: {relative_path} ({optimized_size} bytes)")
            return emotion_data
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save image: {e}")
            raise
    
    def get_session_files(self, session_id: str, user_id: int) -> List[Dict]:
        """Get all files for a session from database"""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                return []
            
            files = []
            for emotion in assessment.emotion_data:
                files.append({
                    'id': emotion.id,
                    'media_type': emotion.media_type,
                    'assessment_type': emotion.assessment_type,
                    'question_identifier': emotion.question_identifier,
                    'file_path': emotion.file_path,
                    'file_size': emotion.file_size,
                    'created_at': emotion.created_at.isoformat() if emotion.created_at else None,
                    'captured_at': emotion.captured_at.isoformat() if emotion.captured_at else None,
                    'full_path': str(self.base_dir / emotion.file_path)
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get session files: {e}")
            return []
    
    def get_user_files(self, user_id: int, session_id: Optional[str] = None) -> List[Dict]:
        """Get all files for a user, optionally filtered by session"""
        try:
            query = db.session.query(EmotionData, Assessment).join(
                Assessment, EmotionData.assessment_id == Assessment.id
            ).filter(Assessment.user_id == user_id)
            
            if session_id:
                query = query.filter(Assessment.session_id == session_id)
            
            files = []
            for emotion, assessment in query.all():
                files.append({
                    'id': emotion.id,
                    'session_id': assessment.session_id,
                    'media_type': emotion.media_type,
                    'assessment_type': emotion.assessment_type,
                    'file_path': emotion.file_path,
                    'file_size': emotion.file_size,
                    'created_at': emotion.created_at.isoformat() if emotion.created_at else None,
                    'captured_at': emotion.captured_at.isoformat() if emotion.captured_at else None,
                    'full_path': str(self.base_dir / emotion.file_path)
                })
            
            return sorted(files, key=lambda x: x['captured_at'] or '', reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get user files: {e}")
            return []
    
    def validate_session_files(self, session_id: str, user_id: int) -> Dict:
        """Validate that all database records have corresponding files"""
        try:
            files = self.get_session_files(session_id, user_id)
            
            total_files = len(files)
            valid_files = 0
            missing_files = []
            
            for file_info in files:
                file_path = Path(file_info['full_path'])
                if file_path.exists():
                    valid_files += 1
                else:
                    missing_files.append(file_info)
            
            return {
                'total_files': total_files,
                'valid_files': valid_files,
                'missing_files': len(missing_files),
                'missing_file_details': missing_files,
                'is_valid': len(missing_files) == 0
            }
            
        except Exception as e:
            logger.error(f"Failed to validate files: {e}")
            return {'error': str(e)}
    
    def cleanup_session_files(self, session_id: str, user_id: int) -> int:
        """Remove all files for a session (VPS files + database records)"""
        try:
            assessment = Assessment.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                return 0
            
            deleted_count = 0
            
            # Delete physical files
            for emotion in assessment.emotion_data:
                file_path = self.base_dir / emotion.file_path
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
            
            # Database records will be deleted by cascade when assessment is deleted
            logger.info(f"Cleaned up {deleted_count} files for session {session_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup session files: {e}")
            return 0
    
    def cleanup_old_files(self) -> Dict:
        """Remove files older than retention_days"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_files = 0
        freed_bytes = 0
        
        try:
            # Get old emotion data records
            old_emotions = EmotionData.query.filter(
                EmotionData.created_at < cutoff_date
            ).all()
            
            for emotion in old_emotions:
                file_path = self.base_dir / emotion.file_path
                if file_path.exists():
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files += 1
                        freed_bytes += file_size
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                
                # Remove database record
                db.session.delete(emotion)
            
            db.session.commit()
            
            # Remove empty directories
            self._remove_empty_dirs(self.base_dir)
            
            logger.info(f"Cleanup complete: {deleted_files} files, {freed_bytes / (1024*1024):.1f}MB freed")
            
            return {
                'deleted_files': deleted_files,
                'freed_bytes': freed_bytes,
                'freed_mb': freed_bytes / (1024*1024)
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Cleanup failed: {e}")
            return {'error': str(e)}
    
    def _remove_empty_dirs(self, path: Path):
        """Recursively remove empty directories"""
        try:
            for subdir in path.iterdir():
                if subdir.is_dir():
                    self._remove_empty_dirs(subdir)
                    try:
                        subdir.rmdir()  # Only removes if empty
                    except OSError:
                        pass  # Directory not empty
        except Exception:
            pass
    
    def get_storage_stats(self) -> Dict:
        """Get storage usage statistics"""
        try:
            # Database stats
            total_records = EmotionData.query.count()
            video_count = EmotionData.query.filter_by(media_type='video').count()
            image_count = EmotionData.query.filter_by(media_type='image').count()
            
            # File system stats
            total_size = 0
            actual_files = 0
            
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
                    actual_files += 1
            
            usage_percent = (total_size / (self.max_storage_gb * 1024 * 1024 * 1024)) * 100
            
            return {
                'database_records': total_records,
                'video_records': video_count,
                'image_records': image_count,
                'actual_files': actual_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_size_gb': total_size / (1024 * 1024 * 1024),
                'usage_percent': usage_percent,
                'max_storage_gb': self.max_storage_gb,
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def _parse_question_start_time(self, metadata: Dict) -> Optional[datetime]:
        """Parse question start time from metadata for correlation"""
        # This will be used to correlate emotion captures with specific user actions
        # For now, return None - will be enhanced when timing correlation is implemented
        return None

# Global instance
emotion_storage = EmotionStorageService()