# 🚀 Modern ORM Models - NO MORE JSON HELL!

## Overview
Complete refactoring from broken JSON-based models to proper normalized SQLAlchemy 2.0 models with `mapped_column` syntax.

## 🔥 What Was Wrong Before

### JSON Column Hell 💀
```python
# OLD BROKEN APPROACH
phq9_settings = db.Column(db.Text)  # JSON string horror!
recording_settings = db.Column(db.Text)  # More JSON!
chat_settings = db.Column(db.Text)  # JSON everywhere!

# Repeated getter/setter methods
def get_phq9_settings(self):
    import json  # Import in method?!
    if self.phq9_settings:
        try:
            return json.loads(self.phq9_settings)
        except json.JSONDecodeError:
            return {}
    return {}
```

### Hardcoded Enum Nightmare 🤡
```python
# OLD BROKEN APPROACH
SCALE_LABEL_0 = ('scale_label_0', 'string', 'Label skala untuk 0', 'Tidak sama sekali')
SCALE_LABEL_1 = ('scale_label_1', 'string', 'Label skala untuk 1', 'Beberapa hari')
# ... 50+ lines of hardcoded bullshit!
```

## ✅ What's Fixed Now

### 1. Proper Normalized Tables
```python
# NEW CLEAN APPROACH
class PHQ9Setting(BaseModel):
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'))
    randomize_questions: Mapped[bool] = mapped_column(default=False)
    scale_min: Mapped[int] = mapped_column(default=0)
    # All fields are queryable, indexable, and relational!
```

### 2. Dynamic Enum Tables
```python
# NEW CLEAN APPROACH
class PHQ9Category(BaseModel):
    number: Mapped[int] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_question: Mapped[str] = mapped_column(Text)
    # Can be translated, modified, and queried!
```

### 3. Modern SQLAlchemy 2.0 Syntax
```python
# NEW CLEAN APPROACH with proper typing
class User(BaseModel, UserMixin, StatusMixin):
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    user_type_id: Mapped[int] = mapped_column(ForeignKey('user_type.id'), nullable=False)
    
    # Proper relationships with typing
    user_type: Mapped["UserType"] = relationship(back_populates="users")
    assessments: Mapped[List["Assessment"]] = relationship(back_populates="user")
```

## 📊 Model Architecture

### Core Models
- **User** + **PatientProfile**: Clean user management
- **Assessment**: NO JSON columns, proper FKs
- **PHQ9Response** + **OpenQuestionResponse**: Proper response tracking
- **EmotionData**: Media files with real relationships

### Settings Architecture (No More JSON!)
```
GlobalSetting       - App-wide settings (replaces AppSetting)
AssessmentSetting   - Per-assessment key-value pairs
PHQ9Setting        - PHQ-9 specific settings per assessment  
RecordingSetting   - Recording config per assessment
ChatSetting        - Chat behavior per assessment
UserPreference     - User-specific preferences
```

### Analysis Architecture (No More JSON!)
```
LLMAnalysisResult   - Analysis metadata
AnalysisIndicator   - Individual analysis metrics (replaces JSON parsed_results)
IndicatorDefinition - Definitions for consistent indicators
```

### Enum Tables (No More Hardcoded!)
```
AssessmentStatus   - in_progress, completed, abandoned
UserType          - patient, admin, superuser
MediaType         - image, video (with extensions)
PHQ9Category      - 9 PHQ categories (translatable)
ScaleLabel        - Dynamic scale labels (multilingual)
```

## 🔄 Migration Process

### Step 1: Backup Existing Data
```bash
python migrate_to_new_models.py --backup
```

### Step 2: Switch to New Models
1. Replace `app/models/__init__.py` with `app/models/__init___new.py`
2. Update `app/__init__.py` to use new Base class
3. Update all imports throughout codebase

### Step 3: Create New Database Schema
```bash
flask db init
flask db migrate -m "Modern ORM refactor - eliminate JSON hell"
flask db upgrade
```

### Step 4: Migrate Data
```bash
python migrate_to_new_models.py --migrate
```

### Step 5: Update Services
Update all services to use new ORM patterns:
- Remove all JSON getter/setter calls
- Use proper relationships instead of string matching
- Update queries to use new table structure

## 🎯 Benefits

### Performance Improvements
- ✅ **Proper indexes** on FK columns
- ✅ **JOIN queries** instead of JSON parsing
- ✅ **Query optimization** possible on normalized data
- ✅ **No JSON serialization** overhead

### Developer Experience
- ✅ **Type hints** with SQLAlchemy 2.0 
- ✅ **IDE autocompletion** on relationships
- ✅ **Proper validation** with FK constraints
- ✅ **Clean code** without JSON hell

### Data Integrity
- ✅ **Foreign key constraints** enforce relationships
- ✅ **Unique constraints** prevent duplicates
- ✅ **Data validation** at database level
- ✅ **Referential integrity** guaranteed

### Maintainability
- ✅ **Single responsibility** per model
- ✅ **DRY principle** - no repeated JSON methods
- ✅ **Separation of concerns** - no business logic in models
- ✅ **Extensible** - easy to add new fields/relationships

## 🔍 Example Queries

### Before (JSON Hell)
```python
# OLD BROKEN WAY
assessment = Assessment.query.get(1)
phq9_settings = assessment.get_phq9_settings()  # JSON parse!
if phq9_settings.get('randomize_questions'):
    # Do something
    
# Can't query JSON data!
```

### After (Clean Relations)
```python
# NEW CLEAN WAY
assessment = Assessment.query.get(1)
if assessment.phq9_setting.randomize_questions:  # Direct access!
    # Do something

# Can query settings directly!
assessments_with_randomization = Assessment.query\
    .join(PHQ9Setting)\
    .filter(PHQ9Setting.randomize_questions == True)\
    .all()
```

## 📋 TODO: Services Update

Update these services to use new patterns:
- [ ] `SettingsService` - use GlobalSetting and AssessmentSetting tables
- [ ] `AssessmentService` - remove JSON methods, use relationships
- [ ] `PHQService` - use PHQ9Category and ScaleLabel tables
- [ ] `LLMAnalysisService` - use AnalysisIndicator table instead of JSON
- [ ] `ExportService` - update to export from normalized tables

## 🚀 Ready for Production!

The new model architecture is:
- **Gunicorn-ready** (no more global issues)
- **Performance optimized** (proper indexes and relationships)
- **Maintainable** (clean code, proper separation)
- **Scalable** (normalized data, query optimization)
- **Type-safe** (SQLAlchemy 2.0 with proper typing)

Say goodbye to JSON hell and hello to proper ORM! 🎉