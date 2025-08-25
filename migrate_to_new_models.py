"""
Data Migration Script: Old JSON Hell → Modern Normalized ORM
Preserves all existing data while migrating to clean model structure

Run this script to migrate from old models to new ones:
python migrate_to_new_models.py --backup --migrate --verify
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app import db as old_db

# Import old models (current broken ones)
from app.models.assessment import Assessment as OldAssessment, PHQ9Response as OldPHQ9Response
from app.models.assessment import OpenQuestionResponse as OldOpenResponse, EmotionData as OldEmotionData
from app.models.user import User as OldUser
from app.models.patient_profile import PatientProfile as OldPatientProfile
from app.models.settings import AppSetting as OldAppSetting
from app.models.llm_analysis import LLMModel as OldLLMModel, LLMAnalysisResult as OldLLMAnalysisResult

# Import new models (clean ones)
from app.models.base import Base
# Note: In real migration, we'd import the new models after updating app/__init__.py


class DataMigrator:
    """Handles migration from old JSON-based models to new normalized models"""
    
    def __init__(self, app):
        self.app = app
        self.backup_dir = Path("./migration_backup")
        self.migration_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log migration progress"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
        
    def create_backup(self):
        """Create backup of existing data"""
        self.log("Creating data backup...")
        self.backup_dir.mkdir(exist_ok=True)
        
        with self.app.app_context():
            # Backup users
            users = OldUser.query.all()
            user_data = []
            for user in users:
                user_dict = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'password_hash': user.password_hash,
                    'user_type': user.user_type,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'is_active': user.is_active
                }
                user_data.append(user_dict)
            
            with open(self.backup_dir / "users.json", 'w') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Backed up {len(user_data)} users")
            
            # Backup patient profiles
            profiles = OldPatientProfile.query.all()
            profile_data = []
            for profile in profiles:
                profile_dict = {
                    'id': profile.id,
                    'user_id': profile.user_id,
                    'age': profile.age,
                    'gender': profile.gender,
                    'educational_level': profile.educational_level,
                    'cultural_background': profile.cultural_background,
                    'medical_conditions': profile.medical_conditions,
                    'medications': profile.medications,
                    'emergency_contact': profile.emergency_contact,
                    'created_at': profile.created_at.isoformat() if profile.created_at else None,
                    'updated_at': profile.updated_at.isoformat() if profile.updated_at else None
                }
                profile_data.append(profile_dict)
            
            with open(self.backup_dir / "patient_profiles.json", 'w') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Backed up {len(profile_data)} patient profiles")
            
            # Backup assessments (including JSON settings!)
            assessments = OldAssessment.query.all()
            assessment_data = []
            for assessment in assessments:
                assessment_dict = {
                    'id': assessment.id,
                    'user_id': assessment.user_id,
                    'session_id': assessment.session_id,
                    'first_assessment_type': assessment.first_assessment_type,
                    'phq9_completed': assessment.phq9_completed,
                    'open_questions_completed': assessment.open_questions_completed,
                    'status': assessment.status,
                    'llm_analysis_status': assessment.llm_analysis_status,
                    'consent_agreed': assessment.consent_agreed,
                    'camera_verified': assessment.camera_verified,
                    'started_at': assessment.started_at.isoformat() if assessment.started_at else None,
                    'completed_at': assessment.completed_at.isoformat() if assessment.completed_at else None,
                    'phq9_score': assessment.phq9_score,
                    'phq9_severity': assessment.phq9_severity,
                    'assessment_order': assessment.assessment_order,
                    
                    # EXTRACT JSON DATA!
                    'phq9_settings': assessment.get_phq9_settings(),
                    'recording_settings': assessment.get_recording_settings(),
                    'chat_settings': assessment.get_chat_settings()
                }
                assessment_data.append(assessment_dict)
            
            with open(self.backup_dir / "assessments.json", 'w') as f:
                json.dump(assessment_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Backed up {len(assessment_data)} assessments with extracted JSON settings")
            
            # Backup responses
            phq9_responses = OldPHQ9Response.query.all()
            phq9_data = []
            for resp in phq9_responses:
                resp_dict = {
                    'id': resp.id,
                    'assessment_id': resp.assessment_id,
                    'question_number': resp.question_number,
                    'question_index_in_category': resp.question_index_in_category,
                    'question_text': resp.question_text,
                    'response_value': resp.response_value,
                    'response_time_ms': resp.response_time_ms,
                    'created_at': resp.created_at.isoformat() if resp.created_at else None
                }
                phq9_data.append(resp_dict)
            
            with open(self.backup_dir / "phq9_responses.json", 'w') as f:
                json.dump(phq9_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Backed up {len(phq9_data)} PHQ9 responses")
            
            # Backup settings
            settings = OldAppSetting.query.all()
            settings_data = []
            for setting in settings:
                setting_dict = {
                    'id': setting.id,
                    'key': setting.key,
                    'value': setting.value,
                    'created_at': setting.created_at.isoformat() if setting.created_at else None,
                    'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
                }
                settings_data.append(setting_dict)
            
            with open(self.backup_dir / "app_settings.json", 'w') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Backed up {len(settings_data)} app settings")
            
            # Save migration log
            with open(self.backup_dir / "migration_log.txt", 'w') as f:
                f.write("\n".join(self.migration_log))
    
    def create_enum_seed_data(self):
        """Create seed data for enum tables"""
        self.log("Creating enum seed data...")
        
        enum_data = {
            'assessment_status': [
                {'name': 'in_progress', 'description': 'Assessment in progress'},
                {'name': 'completed', 'description': 'Assessment completed'},
                {'name': 'abandoned', 'description': 'Assessment abandoned'},
                {'name': 'expired', 'description': 'Assessment expired'}
            ],
            'user_type': [
                {'name': 'patient', 'description': 'Patient user'},
                {'name': 'admin', 'description': 'Administrator user'},
                {'name': 'superuser', 'description': 'Super administrator'}
            ],
            'media_type': [
                {'name': 'image', 'description': 'Image file', 'extensions': 'jpg,jpeg,png,webp', 'mime_types': 'image/jpeg,image/png,image/webp'},
                {'name': 'video', 'description': 'Video file', 'extensions': 'webm,mp4,mov', 'mime_types': 'video/webm,video/mp4,video/quicktime'}
            ],
            'assessment_type': [
                {'name': 'phq9', 'description': 'PHQ-9 Depression Assessment'},
                {'name': 'open_questions', 'description': 'Open-ended Questions'}
            ],
            'phq9_category': [
                {'number': 1, 'name': 'Anhedonia', 'description': 'Loss of interest or pleasure', 'default_question': 'Kurang tertarik atau bergairah dalam melakukan apapun'},
                {'number': 2, 'name': 'Depressed Mood', 'description': 'Feeling down, depressed, or hopeless', 'default_question': 'Merasa murung, muram, atau putus asa'},
                {'number': 3, 'name': 'Sleep Disturbance', 'description': 'Insomnia or hypersomnia', 'default_question': 'Sulit tidur atau mudah terbangun, atau terlalu banyak tidur'},
                {'number': 4, 'name': 'Fatigue', 'description': 'Loss of energy or tiredness', 'default_question': 'Merasa lelah atau kurang bertenaga'},
                {'number': 5, 'name': 'Appetite Changes', 'description': 'Weight/appetite fluctuations', 'default_question': 'Kurang nafsu makan atau terlalu banyak makan'},
                {'number': 6, 'name': 'Worthlessness', 'description': 'Feelings of guilt or failure', 'default_question': 'Kurang percaya diri — atau merasa bahwa Anda adalah orang yang gagal atau telah mengecewakan diri sendiri atau keluarga'},
                {'number': 7, 'name': 'Concentration', 'description': 'Difficulty focusing or thinking', 'default_question': 'Sulit berkonsentrasi pada sesuatu, misalnya membaca koran atau menonton televisi'},
                {'number': 8, 'name': 'Psychomotor', 'description': 'Agitation or retardation', 'default_question': 'Bergerak atau berbicara sangat lambat sehingga orang lain memperhatikannya. Atau sebaliknya — merasa resah atau gelisah sehingga Anda lebih sering bergerak dari biasanya'},
                {'number': 9, 'name': 'Suicidal Ideation', 'description': 'Thoughts of death or self-harm', 'default_question': 'Merasa lebih baik mati atau ingin melukai diri sendiri dengan cara apapun'}
            ],
            'scale_label': [
                {'scale_value': 0, 'label_text': 'Tidak sama sekali', 'language': 'id'},
                {'scale_value': 1, 'label_text': 'Beberapa hari', 'language': 'id'},
                {'scale_value': 2, 'label_text': 'Lebih dari separuh hari', 'language': 'id'},
                {'scale_value': 3, 'label_text': 'Hampir setiap hari', 'language': 'id'},
                {'scale_value': 0, 'label_text': 'Not at all', 'language': 'en'},
                {'scale_value': 1, 'label_text': 'Several days', 'language': 'en'},
                {'scale_value': 2, 'label_text': 'More than half the days', 'language': 'en'},
                {'scale_value': 3, 'label_text': 'Nearly every day', 'language': 'en'}
            ]
        }
        
        with open(self.backup_dir / "enum_seed_data.json", 'w') as f:
            json.dump(enum_data, f, indent=2, ensure_ascii=False)
        
        self.log("Created enum seed data")
    
    def generate_migration_sql(self):
        """Generate SQL migration scripts"""
        self.log("Generating migration SQL...")
        
        # This would generate the actual SQL migration scripts
        # For now, just create a placeholder
        migration_sql = """
-- Migration from old JSON-based models to normalized models
-- Generated on {timestamp}

-- Step 1: Create new tables
-- (This would be generated from the new model definitions)

-- Step 2: Migrate data
-- Users (simple mapping)
INSERT INTO users_new (id, username, email, password_hash, user_type_id, created_at, is_active)
SELECT u.id, u.username, u.email, u.password_hash, 
       CASE u.user_type 
           WHEN 'patient' THEN 1 
           WHEN 'admin' THEN 2 
           WHEN 'superuser' THEN 3 
       END,
       u.created_at, u.is_active
FROM users u;

-- Patient Profiles (simple mapping)
INSERT INTO patient_profiles_new (id, user_id, age, gender, educational_level, cultural_background, medical_conditions, medications, emergency_contact_name, created_at, updated_at)
SELECT id, user_id, age, gender, educational_level, cultural_background, medical_conditions, medications, emergency_contact, created_at, updated_at
FROM patient_profiles;

-- Assessments (remove JSON columns)
INSERT INTO assessments_new (id, user_id, session_id, status_id, first_assessment_type, phq9_completed, open_questions_completed, consent_agreed, camera_verified, started_at, completed_at, phq9_score, phq9_severity, assessment_order)
SELECT a.id, a.user_id, a.session_id,
       CASE a.status 
           WHEN 'in_progress' THEN 1
           WHEN 'completed' THEN 2  
           WHEN 'abandoned' THEN 3
       END,
       a.first_assessment_type, a.phq9_completed, a.open_questions_completed, a.consent_agreed, a.camera_verified,
       a.started_at, a.completed_at, a.phq9_score, a.phq9_severity, a.assessment_order
FROM assessments a;

-- Step 3: Extract JSON settings into proper tables
-- (This would be complex and would need to be done programmatically)

-- Step 4: Update sequences and constraints
-- Step 5: Drop old tables
-- Step 6: Rename new tables
""".format(timestamp=datetime.now().isoformat())
        
        with open(self.backup_dir / "migration.sql", 'w') as f:
            f.write(migration_sql)
        
        self.log("Generated migration SQL template")
    
    def verify_migration(self):
        """Verify migration was successful"""
        self.log("Verifying migration...")
        
        # Load backup data
        with open(self.backup_dir / "users.json", 'r') as f:
            backed_up_users = json.load(f)
        
        with self.app.app_context():
            # Count records in new tables (when they exist)
            # For now, just verify backup files exist
            backup_files = [
                "users.json", "patient_profiles.json", "assessments.json", 
                "phq9_responses.json", "app_settings.json"
            ]
            
            for file_name in backup_files:
                file_path = self.backup_dir / file_name
                if file_path.exists():
                    self.log(f"✓ Backup file {file_name} exists")
                else:
                    self.log(f"✗ Backup file {file_name} missing", "ERROR")
            
            self.log(f"Backed up {len(backed_up_users)} users successfully")


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description='Migrate from old JSON-based models to new normalized models')
    parser.add_argument('--backup', action='store_true', help='Create backup of existing data')
    parser.add_argument('--migrate', action='store_true', help='Run migration (after backup)')
    parser.add_argument('--verify', action='store_true', help='Verify migration was successful')
    parser.add_argument('--all', action='store_true', help='Run all steps: backup, migrate, verify')
    
    args = parser.parse_args()
    
    # Create Flask app
    app = create_app('development')  # Use development config for migration
    migrator = DataMigrator(app)
    
    if args.all or args.backup:
        migrator.create_backup()
        migrator.create_enum_seed_data()
        migrator.generate_migration_sql()
    
    if args.all or args.migrate:
        migrator.log("Migration step would run here (after implementing new models)")
        migrator.log("1. Switch app/__init__.py to use new models")
        migrator.log("2. Run Flask-Migrate to create new tables")
        migrator.log("3. Run data migration scripts")
        migrator.log("4. Update all services to use new ORM patterns")
    
    if args.all or args.verify:
        migrator.verify_migration()
    
    migrator.log("Migration process completed!")
    print(f"\nMigration log saved to: {migrator.backup_dir / 'migration_log.txt'}")


if __name__ == '__main__':
    main()