# app/services/settings.py
from app import db
from app.models.settings import AppSetting
import json

class SettingsException(Exception):
    pass

class SettingsService:
    
    @staticmethod
    def get_all_settings():
        """Get all app settings for display"""
        settings = {}
        
        # Basic settings
        openq_setting = AppSetting.query.filter_by(key='openquestion_prompt').first()
        settings['openquestion_prompt'] = openq_setting.value if openq_setting else ''
        
        consent_setting = AppSetting.query.filter_by(key='consent_form_text').first()
        settings['consent_form_text'] = consent_setting.value if consent_setting else ''
        
        openq_instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()
        settings['openquestion_instructions'] = openq_instructions.value if openq_instructions else ''
        
        phq9_instructions = AppSetting.query.filter_by(key='phq9_instructions').first()
        settings['phq9_instructions'] = phq9_instructions.value if phq9_instructions else ''
        
        # Recording settings
        recording_mode = AppSetting.query.filter_by(key='recording_mode').first()
        settings['recording_mode'] = recording_mode.value if recording_mode else 'capture'
        
        # Image capture settings
        capture_interval = AppSetting.query.filter_by(key='capture_interval').first()
        settings['capture_interval'] = int(capture_interval.value) if capture_interval else 5
        
        image_quality = AppSetting.query.filter_by(key='image_quality').first()
        settings['image_quality'] = float(image_quality.value) if image_quality else 0.8
        
        # Video settings
        video_quality = AppSetting.query.filter_by(key='video_quality').first()
        settings['video_quality'] = video_quality.value if video_quality else '720p'
        
        video_format = AppSetting.query.filter_by(key='video_format').first()
        settings['video_format'] = video_format.value if video_format else 'webm'
        
        # Common settings
        resolution = AppSetting.query.filter_by(key='resolution').first()
        settings['resolution'] = resolution.value if resolution else '1280x720'
        
        enable_recording = AppSetting.query.filter_by(key='enable_recording').first()
        settings['enable_recording'] = enable_recording.value == 'true' if enable_recording else True
        
        # Scale settings
        scale_min = AppSetting.query.filter_by(key='scale_min').first()
        scale_max = AppSetting.query.filter_by(key='scale_max').first()
        
        min_val = int(scale_min.value) if scale_min else 0
        max_val = int(scale_max.value) if scale_max else 3
        
        scale_labels = {}
        for i in range(min_val, max_val + 1):
            label_setting = AppSetting.query.filter_by(key=f'scale_label_{i}').first()
            if label_setting:
                scale_labels[str(i)] = label_setting.value
        
        settings['scale_min'] = min_val
        settings['scale_max'] = max_val
        settings['scale_labels'] = scale_labels
        
        # PHQ settings
        phq9_randomize = AppSetting.query.filter_by(key='phq9_randomize_questions').first()
        settings['phq9_randomize_questions'] = phq9_randomize.value == 'true' if phq9_randomize else False
        
        phq9_progress = AppSetting.query.filter_by(key='phq9_show_progress').first()
        settings['phq9_show_progress'] = phq9_progress.value == 'true' if phq9_progress else True
        
        phq9_per_page = AppSetting.query.filter_by(key='phq9_questions_per_page').first()
        settings['phq9_questions_per_page'] = int(phq9_per_page.value) if phq9_per_page else 1
        
        # PHQ Categories
        from app.models.phq import PHQCategoryType
        settings['phq_category_types'] = PHQCategoryType.get_all_data()
        
        existing_categories = []
        phq_categories = {}
        
        for cat_num in range(1, 10):
            exists_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_exists').first()
            if exists_setting and exists_setting.value == '1':
                existing_categories.append(cat_num)
                
                questions_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_questions').first()
                if questions_setting and questions_setting.value:
                    questions = json.loads(questions_setting.value)
                else:
                    cat_type = PHQCategoryType.get_by_number(cat_num)
                    questions = [cat_type.default_question] if cat_type else []
                
                phq_categories[cat_num] = {'questions': questions}
        
        settings['existing_categories'] = existing_categories
        settings['existing_category_numbers'] = existing_categories
        settings['phq_categories'] = phq_categories
        
        return settings
    
    @staticmethod
    def update_settings(form_data):
        """Update app settings from form data"""
        updated_count = 0
        phq_questions = {}
        
        # Define recording-related keys
        recording_keys = {
            'recording_mode', 'capture_interval', 'image_quality', 
            'video_quality', 'video_format', 'resolution', 'enable_recording'
        }
        
        for key, value in form_data.items():
            if value is None:
                continue
            
            # Handle PHQ category exists flags
            if key.startswith('phq_category_') and key.endswith('_exists'):
                setting = AppSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                else:
                    setting = AppSetting(key=key, value=str(value))
                    db.session.add(setting)
                updated_count += 1
                continue
            
            # Handle PHQ questions
            if key.startswith('phq_category_') and '_question_' in key:
                parts = key.split('_')
                cat_num = int(parts[2])
                if cat_num not in phq_questions:
                    phq_questions[cat_num] = []
                if value.strip():
                    phq_questions[cat_num].append(value.strip())
                continue
            if not key.startswith('phq_') or key in recording_keys:
                setting = AppSetting.query.filter_by(key=key).first()
                if setting:
                    if setting.value != str(value):
                        setting.value = str(value)
                        updated_count += 1
                else:
                    setting = AppSetting(key=key, value=str(value))
                    db.session.add(setting)
                    updated_count += 1
        
        # Save PHQ questions
        for cat_num, questions in phq_questions.items():
            if questions:
                questions_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_questions').first()
                questions_json = json.dumps(questions)
                
                if questions_setting:
                    questions_setting.value = questions_json
                else:
                    questions_setting = AppSetting(key=f'phq_category_{cat_num}_questions', value=questions_json)
                    db.session.add(questions_setting)
                updated_count += 1
        
        db.session.commit()
        return updated_count