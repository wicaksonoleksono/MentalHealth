# app/services/settings.py - Remove try-catch for debugging
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
        
        # Image capture settings
        capture_interval = AppSetting.query.filter_by(key='capture_interval').first()
        settings['capture_interval'] = int(capture_interval.value) if capture_interval else 5
        
        image_quality = AppSetting.query.filter_by(key='image_quality').first()
        settings['image_quality'] = float(image_quality.value) if image_quality else 0.8
        
        image_resolution = AppSetting.query.filter_by(key='image_resolution').first()
        settings['image_resolution'] = image_resolution.value if image_resolution else '1280x720'
        
        enable_capture = AppSetting.query.filter_by(key='enable_capture').first()
        settings['enable_capture'] = enable_capture.value == 'true' if enable_capture else True
        
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
        
        # Get existing categories
        existing_categories = []
        phq_categories = {}
        
        for cat_num in range(1, 10):
            exists_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_exists').first()
            if exists_setting and exists_setting.value == '1':
                existing_categories.append(cat_num)
                
                # Get questions for this category
                questions_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_questions').first()
                if questions_setting and questions_setting.value:
                    questions = json.loads(questions_setting.value)
                else:
                    # Default question from enum
                    cat_type = PHQCategoryType.get_by_number(cat_num)
                    questions = [cat_type.default_question] if cat_type else []
                
                phq_categories[cat_num] = {'questions': questions}
        
        settings['existing_categories'] = existing_categories
        settings['existing_category_numbers'] = existing_categories
        settings['phq_categories'] = phq_categories
        
        return settings
    
    @staticmethod
    def update_settings(form_data):
        """Update app settings from form data - NO TRY-CATCH FOR DEBUGGING"""
        print(f"=== DEBUGGING FORM DATA ===")
        print(f"All form keys: {list(form_data.keys())}")
        
        # Print PHQ-related form data
        phq_data = {k: v for k, v in form_data.items() if k.startswith('phq_')}
        print(f"PHQ form data: {phq_data}")
        
        updated_count = 0
        phq_questions = {}
        
        for key, value in form_data.items():
            if value is None:
                continue
            
            # Handle PHQ category exists flags
            if key.startswith('phq_category_') and key.endswith('_exists'):
                print(f"Processing category exists: {key} = {value}")
                setting = AppSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                    print(f"Updated existing setting: {key}")
                else:
                    setting = AppSetting(key=key, value=str(value))
                    db.session.add(setting)
                    print(f"Added new setting: {key}")
                updated_count += 1
                continue
            
            # Handle PHQ questions
            if key.startswith('phq_category_') and '_question_' in key:
                print(f"Processing question: {key} = {value}")
                parts = key.split('_')
                cat_num = int(parts[2])
                if cat_num not in phq_questions:
                    phq_questions[cat_num] = []
                if value.strip():  # Only add non-empty questions
                    phq_questions[cat_num].append(value.strip())
                    print(f"Added question to category {cat_num}: {value.strip()}")
                continue
            
            # Handle regular settings (non-PHQ)
            if not key.startswith('phq_'):
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
        print(f"PHQ questions to save: {phq_questions}")
        for cat_num, questions in phq_questions.items():
            if questions:  # Only save if there are questions
                questions_setting = AppSetting.query.filter_by(key=f'phq_category_{cat_num}_questions').first()
                questions_json = json.dumps(questions)
                print(f"Saving questions for category {cat_num}: {questions_json}")
                
                if questions_setting:
                    questions_setting.value = questions_json
                    print(f"Updated existing questions for category {cat_num}")
                else:
                    questions_setting = AppSetting(key=f'phq_category_{cat_num}_questions', value=questions_json)
                    db.session.add(questions_setting)
                    print(f"Added new questions for category {cat_num}")
                updated_count += 1
        
        print(f"About to commit {updated_count} changes")
        db.session.commit()
        print(f"Successfully committed changes")
        
        return updated_count