# app/models/phq.py
from app import db
from datetime import datetime
from enum import Enum

class PHQCategoryType(Enum):
    ANHEDONIA = (1, "Anhedonia", "Loss of interest or pleasure")  
    DEPRESSED_MOOD = (2, "Depressed Mood", "Feeling down, depressed, or hopeless")
    SLEEP_DISTURBANCE = (3, "Sleep Disturbance", "Insomnia or hypersomnia")
    FATIGUE = (4, "Fatigue", "Loss of energy or tiredness")
    APPETITE_CHANGES = (5, "Appetite Changes", "Weight/appetite fluctuations")
    WORTHLESSNESS = (6, "Worthlessness", "Feelings of guilt or failure")
    CONCENTRATION = (7, "Concentration", "Difficulty focusing or thinking")
    PSYCHOMOTOR = (8, "Psychomotor", "Agitation or retardation")
    SUICIDAL_IDEATION = (9, "Suicidal Ideation", "Thoughts of death or self-harm")
    
    @property
    def number(self):
        return self.value[0]
    
    @property 
    def name(self):
        return self.value[1]
    
    @property
    def description(self):
        return self.value[2]
    
    @classmethod
    def get_by_number(cls, number):
        for category in cls:
            if category.number == number:
                return category
        return None
    
    @classmethod
    def get_all_data(cls):
        """Return all categories as dict for frontend"""
        return [
            {
                'number': cat.number,
                'name': cat.name, 
                'description': cat.description
            }
            for cat in cls
        ]

class PHQCategory(db.Model):
    __tablename__ = 'phq_category'
    
    id = db.Column(db.Integer, primary_key=True)
    category_number = db.Column(db.Integer, nullable=False, unique=True)
    category_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    questions = db.relationship('PHQQuestion', backref='category', cascade='all, delete-orphan')

class PHQQuestion(db.Model):
    __tablename__ = 'phq_question'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('phq_category.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)