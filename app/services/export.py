# app/services/export.py

import os
import json
import csv
import zipfile
import shutil
from datetime import datetime
from flask import current_app
from app import db
from app.models.assessment import Assessment, PHQ9Response, OpenQuestionResponse, EmotionData
from app.models.user import User
from app.models.patient_profile import PatientProfile
from app.services.media_file import MediaFileService

class ExportException(Exception):
    pass

class ExportService:
    
    @staticmethod
    def export_session_data(session_id, user_id, export_format='zip'):
        """Export all data for a single assessment session"""
        
        # Get assessment
        assessment = Assessment.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise ExportException(f"Assessment session not found: {session_id}")
        
        # Create temporary export directory
        export_dir = ExportService._create_export_directory(session_id)
        
        try:
            # Export metadata
            ExportService._export_session_metadata(assessment, export_dir)
            
            # Export PHQ9 responses
            ExportService._export_phq9_responses(assessment, export_dir)
            
            # Export open question responses
            ExportService._export_open_responses(assessment, export_dir)
            
            # Export media files
            ExportService._export_media_files(assessment, export_dir)
            
            # Export patient profile
            ExportService._export_patient_profile(assessment.user, export_dir)
            
            # Create summary report
            ExportService._create_summary_report(assessment, export_dir)
            
            if export_format == 'zip':
                # Create ZIP file
                zip_path = ExportService._create_zip_file(export_dir, session_id)
                return zip_path
            else:
                return export_dir
                
        finally:
            # Clean up temp directory if ZIP was created
            if export_format == 'zip' and os.path.exists(export_dir):
                shutil.rmtree(export_dir)
    
    @staticmethod
    def export_bulk_data(user_ids=None, date_range=None, export_format='zip'):
        """Export data for multiple sessions/users"""
        
        # Build query
        query = Assessment.query.filter_by(status='completed')
        
        if user_ids:
            query = query.filter(Assessment.user_id.in_(user_ids))
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(
                Assessment.completed_at >= start_date,
                Assessment.completed_at <= end_date
            )
        
        assessments = query.all()
        
        if not assessments:
            raise ExportException("No completed assessments found for export criteria")
        
        # Create bulk export directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = ExportService._create_export_directory(f"bulk_export_{timestamp}")
        
        try:
            # Export each session
            session_dirs = []
            for assessment in assessments:
                session_dir = ExportService._export_single_session_to_dir(assessment, export_dir)
                session_dirs.append(session_dir)
            
            # Create bulk summary
            ExportService._create_bulk_summary(assessments, export_dir)
            
            if export_format == 'zip':
                zip_path = ExportService._create_zip_file(export_dir, f"bulk_export_{timestamp}")
                return zip_path
            else:
                return export_dir
                
        finally:
            if export_format == 'zip' and os.path.exists(export_dir):
                shutil.rmtree(export_dir)
    
    @staticmethod
    def _create_export_directory(session_id):
        """Create temporary export directory"""
        upload_root = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        export_dir = os.path.join(upload_root, 'exports', session_id)
        os.makedirs(export_dir, exist_ok=True)
        return export_dir
    
    @staticmethod
    def _export_session_metadata(assessment, export_dir):
        """Export session metadata as JSON"""
        metadata = {
            'session_info': {
                'session_id': assessment.session_id,
                'user_id': assessment.user_id,
                'status': assessment.status,
                'started_at': assessment.started_at.isoformat() if assessment.started_at else None,
                'completed_at': assessment.completed_at.isoformat() if assessment.completed_at else None,
                'consent_at': assessment.consent_at.isoformat() if assessment.consent_at else None,
                'camera_check_at': assessment.camera_check_at.isoformat() if assessment.camera_check_at else None,
                'first_assessment_started_at': assessment.first_assessment_started_at.isoformat() if assessment.first_assessment_started_at else None
            },
            'assessment_flow': {
                'first_assessment_type': assessment.first_assessment_type,
                'phq9_completed': assessment.phq9_completed,
                'open_questions_completed': assessment.open_questions_completed,
                'consent_agreed': assessment.consent_agreed,
                'camera_verified': assessment.camera_verified
            },
            'results': {
                'phq9_score': assessment.phq9_score,
                'phq9_severity': assessment.phq9_severity
            },
            'completion_order': assessment.get_completion_order(),
            'export_timestamp': datetime.utcnow().isoformat()
        }
        
        with open(os.path.join(export_dir, 'session_metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
    
    @staticmethod
    def _export_phq9_responses(assessment, export_dir):
        """Export PHQ9 responses as CSV and JSON"""
        responses = PHQ9Response.query.filter_by(assessment_id=assessment.id).order_by(PHQ9Response.question_number).all()
        
        if not responses:
            return
        
        # JSON export
        json_data = []
        for response in responses:
            json_data.append({
                'question_number': response.question_number,
                'response_value': response.response_value,
                'response_time_ms': response.response_time_ms,
                'created_at': response.created_at.isoformat()
            })
        
        with open(os.path.join(export_dir, 'phq9_responses.json'), 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # CSV export
        with open(os.path.join(export_dir, 'phq9_responses.csv'), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['question_number', 'response_value', 'response_time_ms', 'created_at'])
            for response in responses:
                writer.writerow([
                    response.question_number,
                    response.response_value,
                    response.response_time_ms,
                    response.created_at.isoformat()
                ])
    
    @staticmethod
    def _export_open_responses(assessment, export_dir):
        """Export open question responses as JSON"""
        responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).order_by(OpenQuestionResponse.created_at).all()
        
        if not responses:
            return
        
        json_data = []
        for response in responses:
            json_data.append({
                'question_text': response.question_text,
                'response_text': response.response_text,
                'response_time_ms': response.response_time_ms,
                'created_at': response.created_at.isoformat()
            })
        
        with open(os.path.join(export_dir, 'open_question_responses.json'), 'w') as f:
            json.dump(json_data, f, indent=2)
    
    @staticmethod
    def _export_media_files(assessment, export_dir):
        """Export all media files with organized structure"""
        emotion_data = EmotionData.query.filter_by(assessment_id=assessment.id).all()
        
        if not emotion_data:
            return
        
        # Create media directory
        media_dir = os.path.join(export_dir, 'media_files')
        os.makedirs(media_dir, exist_ok=True)
        
        # Export file manifest
        manifest = []
        
        for data in emotion_data:
            if data.file_exists():
                # Create organized subdirectory
                sub_dir = os.path.join(media_dir, data.assessment_type, f"{data.media_type}s")
                os.makedirs(sub_dir, exist_ok=True)
                
                # Copy file
                source_path = data.get_full_path()
                filename = f"{data.question_identifier}_{data.id}{os.path.splitext(data.file_path)[1]}"
                dest_path = os.path.join(sub_dir, filename)
                
                shutil.copy2(source_path, dest_path)
                
                # Add to manifest
                manifest.append({
                    'file_id': data.id,
                    'original_path': data.file_path,
                    'export_path': os.path.relpath(dest_path, export_dir),
                    'assessment_type': data.assessment_type,
                    'question_identifier': data.question_identifier,
                    'media_type': data.media_type,
                    'file_size': data.file_size,
                    'mime_type': data.mime_type,
                    'timestamp': data.timestamp.isoformat(),
                    'resolution': data.resolution,
                    'quality_setting': data.quality_setting,
                    'duration_ms': data.duration_ms
                })
        
        # Save manifest
        with open(os.path.join(media_dir, 'file_manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
    
    @staticmethod
    def _export_patient_profile(user, export_dir):
        """Export patient profile data"""
        profile_data = {
            'user_info': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'created_at': user.created_at.isoformat(),
                'is_active': user.is_active
            },
            'patient_profile': None
        }
        
        if user.patient_profile:
            profile = user.patient_profile
            profile_data['patient_profile'] = {
                'age': profile.age,
                'gender': profile.gender,
                'educational_level': profile.educational_level,
                'cultural_background': profile.cultural_background,
                'medical_conditions': profile.medical_conditions,
                'medications': profile.medications,
                'emergency_contact': profile.emergency_contact,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat()
            }
        
        with open(os.path.join(export_dir, 'patient_profile.json'), 'w') as f:
            json.dump(profile_data, f, indent=2)
    
    @staticmethod
    def _create_summary_report(assessment, export_dir):
        """Create human-readable summary report"""
        summary = ExportService._generate_session_summary(assessment)
        
        with open(os.path.join(export_dir, 'summary_report.json'), 'w') as f:
            json.dump(summary, f, indent=2)
    
    @staticmethod
    def _create_zip_file(export_dir, filename):
        """Create ZIP file from export directory"""
        upload_root = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        zip_path = os.path.join(upload_root, 'exports', f"{filename}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, export_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    @staticmethod
    def _generate_session_summary(assessment):
        """Generate comprehensive session summary"""
        files = MediaFileService.get_session_files(assessment.session_id, assessment.user_id)
        
        return {
            'session_id': assessment.session_id,
            'completion_status': assessment.status,
            'duration_minutes': None,  # Calculate if possible
            'assessment_scores': {
                'phq9_score': assessment.phq9_score,
                'phq9_severity': assessment.phq9_severity
            },
            'media_capture_summary': {
                'total_files': len(files),
                'images_captured': len([f for f in files if f['media_type'] == 'image']),
                'videos_captured': len([f for f in files if f['media_type'] == 'video']),
                'total_file_size_mb': round(sum(f['file_size'] for f in files if f['file_size']) / (1024*1024), 2)
            },
            'assessment_flow': assessment.get_completion_order()
        }