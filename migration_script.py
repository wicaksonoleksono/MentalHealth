#!/usr/bin/env python3
"""
Database migration script to add new fields to EmotionData table.

This script adds the following fields to the EmotionData table:
- capture_timestamp (BigInteger)
- time_into_question_ms (Integer)
- recording_settings (Text)

Run this script after updating the models to add the new columns.
"""

from flask import Flask
from app import create_app, db
from app.models.assessment import EmotionData

def migrate_database():
    """Add new columns to EmotionData table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('emotion_data')]
            
            # Add missing columns
            if 'capture_timestamp' not in existing_columns:
                db.engine.execute('ALTER TABLE emotion_data ADD COLUMN capture_timestamp BIGINT')
                print("✓ Added capture_timestamp column")
            else:
                print("• capture_timestamp column already exists")
            
            if 'time_into_question_ms' not in existing_columns:
                db.engine.execute('ALTER TABLE emotion_data ADD COLUMN time_into_question_ms INTEGER')
                print("✓ Added time_into_question_ms column")
            else:
                print("• time_into_question_ms column already exists")
            
            if 'recording_settings' not in existing_columns:
                db.engine.execute('ALTER TABLE emotion_data ADD COLUMN recording_settings TEXT')
                print("✓ Added recording_settings column")
            else:
                print("• recording_settings column already exists")
            
            print("\n✅ Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Starting database migration...")
    migrate_database()