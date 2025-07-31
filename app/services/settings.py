# app/services/settings.py
from app import db
from app.models.settings import AppSetting
from app.services.phq import PHQ
import logging

logger = logging.getLogger(__name__)

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
            
            # Get instruction texts
            openq_instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()
            settings['openquestion_instructions'] = openq_instructions.value if openq_instructions else ''
            
            phq9_instructions = AppSetting.query.filter_by(key='phq9_instructions').first()
            settings['phq9_instructions'] = phq9_instructions.value if phq9_instructions else ''
            
            # Get image capture settings
            capture_interval = AppSetting.query.filter_by(key='capture_interval').first()
            settings['capture_interval'] = int(capture_interval.value) if capture_interval else 5
            
            image_quality = AppSetting.query.filter_by(key='image_quality').first()
            settings['image_quality'] = float(image_quality.value) if image_quality else 0.8
            
            image_resolution = AppSetting.query.filter_by(key='image_resolution').first()
            settings['image_resolution'] = image_resolution.value if image_resolution else '1280x720'
            
            enable_capture = AppSetting.query.filter_by(key='enable_capture').first()
            settings['enable_capture'] = enable_capture.value == 'true' if enable_capture else True
            
            # Add PHQ scale settings
            settings.update(SettingsService.get_scale_settings())
            
            # Add additional PHQ settings
            phq9_randomize = AppSetting.query.filter_by(key='phq9_randomize_questions').first()
            settings['phq9_randomize_questions'] = phq9_randomize.value == 'true' if phq9_randomize else False
            
            phq9_progress = AppSetting.query.filter_by(key='phq9_show_progress').first()
            settings['phq9_show_progress'] = phq9_progress.value == 'true' if phq9_progress else True
            
            phq9_per_page = AppSetting.query.filter_by(key='phq9_questions_per_page').first()
            settings['phq9_questions_per_page'] = int(phq9_per_page.value) if phq9_per_page else 1
            
            return settings
            
        except Exception as e:
            logger.error(f"Failed to load settings: {str(e)}")
            raise SettingsException(f"Failed to load settings: {str(e)}")
    
    @staticmethod
    def get_scale_settings():
        """Get PHQ scale settings for the component"""
        try:
            # Get scale range
            scale_min = AppSetting.query.filter_by(key='scale_min').first()
            scale_max = AppSetting.query.filter_by(key='scale_max').first()
            
            min_val = int(scale_min.value) if scale_min else 0
            max_val = int(scale_max.value) if scale_max else 3
            
            # Get all scale labels for the range
            scale_labels = {}
            for i in range(min_val, max_val + 1):
                label_setting = AppSetting.query.filter_by(key=f'scale_label_{i}').first()
                if label_setting:
                    scale_labels[str(i)] = label_setting.value
            
            return {
                'scale_min': min_val,
                'scale_max': max_val,
                'scale_labels': scale_labels
            }
            
        except Exception as e:
            logger.error(f"Failed to load scale settings: {str(e)}")
            raise SettingsException(f"Failed to load scale settings: {str(e)}")
    
    @staticmethod
    def update_settings(form_data):
        """Update app settings from form data"""
        try:
            logger.info(f"Updating settings with data: {list(form_data.keys())}")
            
            updated_count = 0
            for key, value in form_data.items():
                if value is None:
                    continue
                    
                setting = AppSetting.query.filter_by(key=key).first()
                if setting:
                    if setting.value != str(value):
                        setting.value = str(value)
                        updated_count += 1
                else:
                    setting = AppSetting(key=key, value=str(value))
                    db.session.add(setting)
                    updated_count += 1
            
            db.session.commit()
            logger.info(f"Successfully updated {updated_count} settings")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save settings: {str(e)}")
            raise SettingsException(f"Failed to save settings: {str(e)}")
    
    @staticmethod
    def get_phq_management_data():
        """Get PHQ categories and questions for management interface"""
        try:
            return PHQ.get_categories_with_questions()
        except Exception as e:
            logger.error(f"Failed to load PHQ data: {str(e)}")
            raise SettingsException(f"Failed to load PHQ data: {str(e)}")