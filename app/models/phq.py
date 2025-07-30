# app/models/phq.py
from app import db
from datetime import datetime
from enum import Enum

class PHQCategoryType(Enum):
    ANHEDONIA = (1, "Anhedonia", "Loss of interest or pleasure", "Kurang tertarik atau bergairah dalam melakukan apapun")
    DEPRESSED_MOOD = (2, "Depressed Mood", "Feeling down, depressed, or hopeless", "Merasa murung, muram, atau putus asa")
    SLEEP_DISTURBANCE = (3, "Sleep Disturbance", "Insomnia or hypersomnia", "Sulit tidur atau mudah terbangun, atau terlalu banyak tidur")
    FATIGUE = (4, "Fatigue", "Loss of energy or tiredness", "Merasa lelah atau kurang bertenaga")
    APPETITE_CHANGES = (5, "Appetite Changes", "Weight/appetite fluctuations", "Kurang nafsu makan atau terlalu banyak makan")
    WORTHLESSNESS = (6, "Worthlessness", "Feelings of guilt or failure", "Kurang percaya diri — atau merasa bahwa Anda adalah orang yang gagal atau telah mengecewakan diri sendiri atau keluarga")
    CONCENTRATION = (7, "Concentration", "Difficulty focusing or thinking", "Sulit berkonsentrasi pada sesuatu, misalnya membaca koran atau menonton televisi")
    PSYCHOMOTOR = (8, "Psychomotor", "Agitation or retardation", "Bergerak atau berbicara sangat lambat sehingga orang lain memperhatikannya. Atau sebaliknya — merasa resah atau gelisah sehingga Anda lebih sering bergerak dari biasanya")
    SUICIDAL_IDEATION = (9, "Suicidal Ideation", "Thoughts of death or self-harm", "Merasa lebih baik mati atau ingin melukai diri sendiri dengan cara apapun")

    @property
    def number(self):
        return self.value[0]

    @property
    def name(self):
        return self.value[1]

    @property
    def description(self):
        return self.value[2]
    
    @property
    def default_question(self):
        return self.value[3]

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
                'description': cat.description,
                'default_question': cat.default_question
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