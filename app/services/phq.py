# app/services/phq.py
from app import db
from app.models.phq import PHQCategory, PHQQuestion, PHQCategoryType

class PHQException(Exception):
    pass

class PHQ:
    
    @staticmethod
    def get_available_categories():
        """Get categories not yet created"""
        try:
            existing_numbers = {cat.category_number for cat in PHQCategory.query.all()}
            available = []
            
            for category_type in PHQCategoryType:
                if category_type.number not in existing_numbers:
                    available.append({
                        'number': category_type.number,
                        'name': category_type.name,
                        'description': category_type.description
                    })
            
            return available
        except Exception as e:
            raise PHQException(f"Failed to get available categories: {str(e)}")
    
    @staticmethod
    def get_categories_with_questions():
        """Get all categories with their questions for display"""
        try:
            categories = PHQCategory.query.order_by(PHQCategory.category_number).all()
            result = []
            
            for category in categories:
                questions = PHQQuestion.query.filter_by(category_id=category.id).all()
                result.append({
                    'category': category,
                    'questions': questions
                })
            
            return {'categories': result}
        except Exception as e:
            raise PHQException(f"Failed to load categories: {str(e)}")
    
    @staticmethod
    def create_category(category_number, category_name=None, description=None):
        """Create new PHQ category"""
        try:
            # Check if already exists
            if PHQCategory.query.filter_by(category_number=category_number).first():
                raise PHQException(f"Category {category_number} already exists")
            
            # Get defaults from enum
            category_type = PHQCategoryType.get_by_number(category_number)
            if not category_type:
                raise PHQException(f"Invalid category number: {category_number}")
            
            category = PHQCategory(
                category_number=category_number,
                category_name=category_name or category_type.name,
                description=description or category_type.description
            )
            
            db.session.add(category)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to create category: {str(e)}")
    
    @staticmethod
    def create_all_standard_categories():
        """Create all 9 standard PHQ-9 categories"""
        try:
            created_count = 0
            existing_numbers = {cat.category_number for cat in PHQCategory.query.all()}
            
            for category_type in PHQCategoryType:
                if category_type.number not in existing_numbers:
                    category = PHQCategory(
                        category_number=category_type.number,
                        category_name=category_type.name,
                        description=category_type.description
                    )
                    db.session.add(category)
                    created_count += 1
            
            db.session.commit()
            return created_count
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to create categories: {str(e)}")
    
    @staticmethod
    def add_question_to_category(category_number, question_text):
        """Add question to existing category"""
        try:
            category = PHQCategory.query.filter_by(category_number=category_number).first()
            if not category:
                raise PHQException(f"Category {category_number} not found")
            
            question = PHQQuestion(
                category_id=category.id,
                question_text=question_text.strip()
            )
            
            db.session.add(question)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to add question: {str(e)}")
    
    @staticmethod
    def update_question(question_id, data):
        """Update existing question"""
        try:
            question = PHQQuestion.query.get(question_id)
            if not question:
                raise PHQException(f"Question {question_id} not found")
            
            if 'question_text' in data:
                question.question_text = data['question_text'].strip()
            
            if 'is_active' in data:
                question.is_active = data['is_active']
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to update question: {str(e)}")
    
    @staticmethod
    def delete_question(question_id):
        """Delete question"""
        try:
            question = PHQQuestion.query.get(question_id)
            if not question:
                raise PHQException(f"Question {question_id} not found")
            
            db.session.delete(question)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to delete question: {str(e)}")
    
    @staticmethod
    def delete_category(category_number):
        """Delete category and all its questions"""
        try:
            category = PHQCategory.query.filter_by(category_number=category_number).first()
            if not category:
                raise PHQException(f"Category {category_number} not found")
            
            db.session.delete(category)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise PHQException(f"Failed to delete category: {str(e)}")