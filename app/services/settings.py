# app/services/settings.py - Clean version

from app import db
from app.models.settings import AppSetting,SettingsKey
import json
class SettingsException(Exception):
    pass
class SettingsService:
    @staticmethod
    def get(setting_key):
        """Get single setting value by enum key"""
        if isinstance(setting_key, str):
            setting_key = SettingsKey.get_by_key(setting_key)
        
        if not setting_key:
            raise SettingsException(f"Unknown setting key")
        
        setting = AppSetting.query.filter_by(key=setting_key.key).first()
        
        if not setting:
            return setting_key.default
        
        # Convert based on data type
        return SettingsService._convert_value(setting.value, setting_key.data_type)
    
    @staticmethod
    def set(setting_key, value):
        """Set single setting value"""
        if isinstance(setting_key, str):
            setting_key = SettingsKey.get_by_key(setting_key)
        
        if not setting_key:
            raise SettingsException(f"Unknown setting key")
        
        # Validate value
        validated_value = SettingsService._validate_value(value, setting_key)
        
        # Get or create setting
        setting = AppSetting.query.filter_by(key=setting_key.key).first()
        
        # Convert boolean to string representation that _convert_value can handle
        if setting_key.data_type == 'boolean':
            stored_value = '1' if validated_value else '0'
        else:
            stored_value = str(validated_value)
            
        if setting:
            setting.value = stored_value
        else:
            setting = AppSetting(key=setting_key.key, value=stored_value)
            db.session.add(setting)
        
        db.session.commit()
        return validated_value
    
    @staticmethod
    def get_group(group_method):
        """Get all settings for a group (recording, phq9, etc.)"""
        if isinstance(group_method, str):
            group_method = getattr(SettingsKey, f'get_{group_method}_settings')
        
        settings_keys = group_method()
        result = {}
        
        for setting_key in settings_keys:
            result[setting_key.key] = SettingsService.get(setting_key)
        
        return result
    
    @staticmethod
    def get_all():
        """Get all settings organized by category"""
        return {
            'recording': SettingsService.get_group(SettingsKey.get_recording_settings),
            'phq9': SettingsService.get_group(SettingsKey.get_phq9_settings),
            'text': SettingsService.get_group(SettingsKey.get_text_settings),
            'llm': SettingsService.get_group(SettingsKey.get_llm_settings)
        }
    
    @staticmethod
    def update_bulk(settings_dict):
        """Update multiple settings at once"""
        updated_count = 0
        
        # Handle PHQ category data first
        phq_categories = {}
        other_settings = {}
        
        for key, value in settings_dict.items():
            if key.startswith('phq_category_') and key.endswith('_exists'):
                # PHQ category exists flag
                cat_num = key.split('_')[2]
                if cat_num not in phq_categories:
                    phq_categories[cat_num] = {'exists': True, 'questions': [], 'name': f'Category {cat_num}'}
            elif key.startswith('phq_category_') and key.endswith('_name'):
                # PHQ category name
                cat_num = key.split('_')[2]
                if cat_num not in phq_categories:
                    phq_categories[cat_num] = {'exists': True, 'questions': [], 'name': value}
                else:
                    phq_categories[cat_num]['name'] = value
            elif key.startswith('phq_category_') and '_question_' in key:
                # PHQ category question
                parts = key.split('_')
                cat_num = parts[2]
                question_idx = int(parts[4])
                if cat_num not in phq_categories:
                    phq_categories[cat_num] = {'exists': True, 'questions': [], 'name': f'Category {cat_num}'}
                # Ensure questions list is long enough
                while len(phq_categories[cat_num]['questions']) <= question_idx:
                    phq_categories[cat_num]['questions'].append('')
                phq_categories[cat_num]['questions'][question_idx] = value
            else:
                other_settings[key] = value
        
        # Save PHQ category data as JSON
        import json
        for cat_num, data in phq_categories.items():
            if data['exists']:
                # Save existence flag
                exists_key = f'phq_category_{cat_num}_exists'
                SettingsService._save_raw_setting(exists_key, '1')
                updated_count += 1
                
                # Save category name
                name_key = f'phq_category_{cat_num}_name'
                SettingsService._save_raw_setting(name_key, data['name'])
                updated_count += 1
                
                # Save questions as JSON
                questions_key = f'phq_category_{cat_num}_questions'
                # Filter out empty questions
                questions = [q for q in data['questions'] if q.strip()]
                SettingsService._save_raw_setting(questions_key, json.dumps(questions))
                updated_count += 1
        
        # Handle regular settings
        for key, value in other_settings.items():
            setting_key = SettingsKey.get_by_key(key)
            if setting_key:
                SettingsService.set(setting_key, value)
                updated_count += 1
        
        return updated_count
    
    @staticmethod
    def reset_to_defaults():
        """Reset all settings to their default values"""
        reset_count = 0
        
        for setting_key in SettingsKey:
            if setting_key.default is not None:
                SettingsService.set(setting_key, setting_key.default)
                reset_count += 1
        
        return reset_count
    
    @staticmethod
    def get_recording_config():
        """ Get recording configuration for frontend with scientific capture modes"""
        recording_settings = SettingsService.get_group(SettingsKey.get_recording_settings)
        
        # Provide defaults if settings aren't configured
        return {
            # Legacy settings
            'mode': recording_settings.get('recording_mode', 'capture'),
            'enabled': recording_settings.get('enable_recording', True),
            
            'capture_mode': recording_settings.get('capture_mode', 'interval'),
            
            # Interval settings
            'interval': recording_settings.get('capture_interval', 5),
            
            # Event-driven settings
            'event_capture_enabled': recording_settings.get('event_capture_enabled', True),
            'capture_on_button_click': recording_settings.get('capture_on_button_click', True),
            'capture_on_message_send': recording_settings.get('capture_on_message_send', True),
            'capture_on_question_start': recording_settings.get('capture_on_question_start', False),
            'capture_on_typing_pause': recording_settings.get('capture_on_typing_pause', False),
            
            # Technical settings
            'resolution': recording_settings.get('resolution', '1280x720'),
            'image_quality': recording_settings.get('image_quality', 0.8),
            'video_quality': recording_settings.get('video_quality', '720p'),
            'video_format': recording_settings.get('video_format', 'webm')
        }
    
    @staticmethod
    def get_phq9_config():
        """Get PHQ9 configuration for frontend"""
        phq9_settings = SettingsService.get_group(SettingsKey.get_phq9_settings)
        
        # Build scale labels
        scale_labels = {}
        min_val = phq9_settings['scale_min']
        max_val = phq9_settings['scale_max']
        
        for i in range(min_val, max_val + 1):
            label_key = f'scale_label_{i}'
            if label_key in phq9_settings:
                scale_labels[str(i)] = phq9_settings[label_key]
        
        return {
            'instructions': phq9_settings['phq9_instructions'],
            'randomize': phq9_settings['phq9_randomize_questions'],
            'scale': {
                'min': min_val,
                'max': max_val,
                'labels': scale_labels
            }
        }
    @staticmethod
    def _convert_value(value, data_type):
        """Convert string value to proper type"""
        if value is None:
            return None
        
        if data_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'integer':
            return int(value)
        elif data_type == 'float':
            return float(value)
        else:  # string, text, choice
            return value
    
    @staticmethod
    def _save_raw_setting(key, value):
        """Save raw setting value without validation"""
        setting = AppSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = AppSetting(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()
    
    @staticmethod
    def _validate_value(value, setting_key):
        """Validate value against setting constraints"""
        if setting_key.data_type == 'choice' and setting_key.choices:
            if value not in setting_key.choices:
                raise SettingsException(f"Invalid choice for {setting_key.key}: {value}")
        
        if setting_key.data_type == 'float':
            if setting_key.key == 'image_quality' and not (0.1 <= float(value) <= 1.0):
                raise SettingsException("Image quality must be between 0.1 and 1.0")
        
        if setting_key.data_type == 'integer':
            if setting_key.key == 'capture_interval' and int(value) < 1:
                raise SettingsException("Capture interval must be at least 1 second")
        
        return value