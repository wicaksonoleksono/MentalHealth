# app/services/settings.py
from app import db
from app.models.settings import AppSetting
from app.services.phq import PHQ

class SettingsException(Exception):
    pass

class SettingsService:
    
    @staticmethod
    def get_all_settings():
        """Get all app settings for display"""
        try:
            settings = {}
            
            # Get openquestion prompt
            openq_setting = AppSetting.query.filter_by(key='openquestion_prompt').first()
            settings['openquestion_prompt'] = openq_setting.value if openq_setting else ''
            
            # Get consent form text
            consent_setting = AppSetting.query.filter_by(key='consent_form_text').first()
            settings['consent_form_text'] = consent_setting.value if consent_setting else ''
            
            # Get image capture settings
            capture_interval = AppSetting.query.filter_by(key='capture_interval').first()
            settings['capture_interval'] = int(capture_interval.value) if capture_interval else 5
            
            image_quality = AppSetting.query.filter_by(key='image_quality').first()
            settings['image_quality'] = float(image_quality.value) if image_quality else 0.8
            
            image_resolution = AppSetting.query.filter_by(key='image_resolution').first()
            settings['image_resolution'] = image_resolution.value if image_resolution else '1280x720'
            
            enable_capture = AppSetting.query.filter_by(key='enable_capture').first()
            settings['enable_capture'] = enable_capture.value == 'true' if enable_capture else True
            
            return settings
            
        except Exception as e:
            raise SettingsException(f"Failed to load settings: {str(e)}")
    
    @staticmethod
    def update_settings(form_data):
        """Update app settings from form data"""
        try:
            for key, value in form_data.items():
                if value is None:
                    continue
                    
                setting = AppSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    setting = AppSetting(key=key, value=value)
                    db.session.add(setting)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise SettingsException(f"Failed to save settings: {str(e)}")
    
    @staticmethod
    def get_phq_management_data():
        """Get PHQ categories and questions for management interface"""
        try:
            return PHQ.get_categories_with_questions()
        except Exception as e:
            raise SettingsException(f"Failed to load PHQ data: {str(e)}")