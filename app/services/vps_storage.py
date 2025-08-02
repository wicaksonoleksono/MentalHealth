"""
VPS-Optimized File Storage Service
Handles video/image storage with organized structure and automatic cleanup
"""
import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class VPSStorageService:
    def __init__(self, base_dir: str = "./uploads"):
        self.base_dir = Path(base_dir)
        self.max_storage_gb = 10  # Total storage limit
        self.retention_days = 30  # Auto-delete after 30 days
        self.max_file_size_mb = 50  # Individual file size limit
        self.image_quality = 85  # JPEG compression quality
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def get_storage_path(self, user_id: int, session_id: str, assessment_type: str) -> Path:
        """Generate organized storage path: /uploads/YYYY/MM/DD/user_123/assessment_type/session_456/"""
        date_path = datetime.now().strftime('%Y/%m/%d')
        return self.base_dir / date_path / f"user_{user_id}" / assessment_type / f"session_{session_id}"
    
    def save_video(self, user_id: int, session_id: str, assessment_type: str, 
                   video_data: bytes, filename: str, metadata: Dict) -> Dict:
        """Save video file with organized structure"""
        try:
            # Check file size
            file_size_mb = len(video_data) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                raise ValueError(f"File too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB")
            
            # Create storage path
            storage_path = self.get_storage_path(user_id, session_id, assessment_type)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"video_{timestamp}.webm"
            file_path = storage_path / safe_filename
            
            # Save video file
            with open(file_path, 'wb') as f:
                f.write(video_data)
            
            # Save metadata
            metadata_path = storage_path / f"video_{timestamp}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump({
                    'original_filename': filename,
                    'file_size_bytes': len(video_data),
                    'created_at': datetime.now().isoformat(),
                    'user_id': user_id,
                    'session_id': session_id,
                    'assessment_type': assessment_type,
                    **metadata
                }, f, indent=2)
            
            logger.info(f"Video saved: {file_path} ({file_size_mb:.1f}MB)")
            
            return {
                'file_path': str(file_path),
                'file_size': len(video_data),
                'filename': safe_filename,
                'metadata_path': str(metadata_path),
                'relative_path': str(file_path.relative_to(self.base_dir))
            }
            
        except Exception as e:
            logger.error(f"Failed to save video: {e}")
            raise
    
    def save_image(self, user_id: int, session_id: str, assessment_type: str,
                   image_data: bytes, filename: str, metadata: Dict) -> Dict:
        """Save and optimize image file"""
        try:
            # Create storage path
            storage_path = self.get_storage_path(user_id, session_id, assessment_type)
            images_path = storage_path / "images"
            images_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            safe_filename = f"capture_{timestamp}.jpg"
            file_path = images_path / safe_filename
            
            # Save and optimize image
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Optimize image with PIL
            try:
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Save with optimization
                    img.save(file_path, 'JPEG', optimize=True, quality=self.image_quality)
                    
                optimized_size = file_path.stat().st_size
                logger.info(f"Image optimized: {len(image_data)} -> {optimized_size} bytes")
                
            except Exception as e:
                logger.warning(f"Image optimization failed: {e}")
                optimized_size = len(image_data)
            
            # Save metadata
            metadata_path = images_path / f"capture_{timestamp}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump({
                    'original_filename': filename,
                    'original_size_bytes': len(image_data),
                    'optimized_size_bytes': optimized_size,
                    'created_at': datetime.now().isoformat(),
                    'user_id': user_id,
                    'session_id': session_id,
                    'assessment_type': assessment_type,
                    'image_quality': self.image_quality,
                    **metadata
                }, f, indent=2)
            
            return {
                'file_path': str(file_path),
                'file_size': optimized_size,
                'filename': safe_filename,
                'metadata_path': str(metadata_path),
                'relative_path': str(file_path.relative_to(self.base_dir))
            }
            
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise
    
    def cleanup_old_files(self) -> Dict:
        """Remove files older than retention_days"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_files = 0
        freed_bytes = 0
        
        try:
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check file age
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files += 1
                            freed_bytes += file_size
                            logger.info(f"Deleted old file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete {file_path}: {e}")
            
            # Remove empty directories
            self._remove_empty_dirs(self.base_dir)
            
            logger.info(f"Cleanup complete: {deleted_files} files, {freed_bytes / (1024*1024):.1f}MB freed")
            
            return {
                'deleted_files': deleted_files,
                'freed_bytes': freed_bytes,
                'freed_mb': freed_bytes / (1024*1024)
            }
            
        except Exception as e:
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
                        pass  # Directory not empty, that's fine
        except Exception:
            pass
    
    def get_storage_stats(self) -> Dict:
        """Get current storage usage statistics"""
        try:
            total_size = 0
            total_files = 0
            file_types = {'videos': 0, 'images': 0, 'metadata': 0}
            
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = Path(root) / file
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    total_files += 1
                    
                    # Categorize file types
                    if file.endswith(('.webm', '.mp4', '.avi')):
                        file_types['videos'] += 1
                    elif file.endswith(('.jpg', '.jpeg', '.png')):
                        file_types['images'] += 1
                    elif file.endswith('.json'):
                        file_types['metadata'] += 1
            
            usage_percent = (total_size / (self.max_storage_gb * 1024 * 1024 * 1024)) * 100
            
            return {
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_size_gb': total_size / (1024 * 1024 * 1024),
                'total_files': total_files,
                'file_types': file_types,
                'usage_percent': usage_percent,
                'max_storage_gb': self.max_storage_gb,
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def get_user_files(self, user_id: int, session_id: Optional[str] = None) -> List[Dict]:
        """Get files for a specific user and optionally session"""
        files = []
        
        try:
            # Search pattern: user_123 directories
            user_pattern = f"user_{user_id}"
            
            for root, dirs, filenames in os.walk(self.base_dir):
                if user_pattern in root:
                    # Filter by session if specified
                    if session_id and f"session_{session_id}" not in root:
                        continue
                    
                    for filename in filenames:
                        if not filename.endswith('_metadata.json'):
                            file_path = Path(root) / filename
                            metadata_path = Path(root) / f"{filename.rsplit('.', 1)[0]}_metadata.json"
                            
                            # Load metadata if exists
                            metadata = {}
                            if metadata_path.exists():
                                try:
                                    with open(metadata_path) as f:
                                        metadata = json.load(f)
                                except Exception:
                                    pass
                            
                            files.append({
                                'filename': filename,
                                'file_path': str(file_path),
                                'relative_path': str(file_path.relative_to(self.base_dir)),
                                'file_size': file_path.stat().st_size,
                                'created_at': metadata.get('created_at'),
                                'assessment_type': metadata.get('assessment_type'),
                                'session_id': metadata.get('session_id'),
                                'metadata': metadata
                            })
            
            # Sort by creation time
            files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get user files: {e}")
            return []

# Global instance
vps_storage = VPSStorageService()