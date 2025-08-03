#!/usr/bin/env python3
# create_llm_tables.py - Create LLM analysis tables

from app import create_app, db
from app.models.llm_analysis import LLMModel, LLMAnalysisResult, AnalysisConfiguration

def create_llm_tables():
    """Create LLM analysis tables and initialize default configuration"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✓ LLM analysis tables created successfully!")
            
            # Check if default configuration exists
            existing_config = AnalysisConfiguration.get_active_config()
            if not existing_config:
                # Create default analysis configuration
                default_config = AnalysisConfiguration(
                    instruction_prompt="""Berdasarkan indikator-indikator dari gejala depresi berikut:
Anhedonia (kehilangan minat/kenikmatan)
Bias kognitif negatif & hopelessness
Rumination (pikiran berputar tanpa solusi)
Psikomotor retardation
Gangguan tidur (insomnia, kualitas tidur jelek)
Iritabilitas & ledakan marah
Rasa bersalah berlebih / self‑blame
Gangguan kognitif (concentration & executive function)
Penarikan diri sosial / isolasi
Alexithymia (sulit mengenali & mengungkap emosi)
Defisit regulasi emosi
Buatlah analisa jawaban "Teman" diatas untuk setiap indikator tersebut beserta penilaian skala angka (0-3) yang diberikan untuk menunjukkan sejauh mana indikasi gejala tersebut muncul dalam percakapan:
0: Tidak Ada Indikasi Jelas (Gejala tidak muncul dalam percakapan)
1: Indikasi Ringan (Gejala tersirat atau disebutkan secara tidak langsung)
2: Indikasi Sedang (Gejala disebutkan dengan cukup jelas, namun tidak mendominasi)
3: Indikasi Kuat (Gejala disebutkan secara eksplisit, berulang, dan menjadi keluhan utama)""",
                    format_prompt="""Gunakan format
{
  "anhedonia": {
    "penjelasan": "analisis untuk anhedonia",
    "skor": 0
  },
  "bias_kognitif_negatif": {
    "penjelasan": "analisis untuk bias kognitif negatif & hopelessness",
    "skor": 0
  },
  "rumination": {
    "penjelasan": "analisis untuk rumination",
    "skor": 0
  },
  "psikomotor_retardation": {
    "penjelasan": "analisis untuk psikomotor retardation",
    "skor": 0
  },
  "gangguan_tidur": {
    "penjelasan": "analisis untuk gangguan tidur",
    "skor": 0
  },
  "iritabilitas": {
    "penjelasan": "analisis untuk iritabilitas & ledakan marah",
    "skor": 0
  },
  "rasa_bersalah": {
    "penjelasan": "analisis untuk rasa bersalah berlebih / self-blame",
    "skor": 0
  },
  "gangguan_kognitif": {
    "penjelasan": "analisis untuk gangguan kognitif",
    "skor": 0
  },
  "penarikan_diri_sosial": {
    "penjelasan": "analisis untuk penarikan diri sosial / isolasi",
    "skor": 0
  },
  "alexithymia": {
    "penjelasan": "analisis untuk alexithymia",
    "skor": 0
  },
  "defisit_regulasi_emosi": {
    "penjelasan": "analisis untuk defisit regulasi emosi",
    "skor": 0
  }
}""",
                    is_active=True
                )
                
                db.session.add(default_config)
                db.session.commit()
                print("✓ Default analysis configuration created!")
            else:
                print("✓ Analysis configuration already exists")
                
            print("\n🎉 LLM Analysis system initialized successfully!")
            print("\nNext steps:")
            print("1. Configure your API keys in .env file:")
            print("   - OPENAI_API_KEY=your_openai_key")
            print("   - ANTHROPIC_API_KEY=your_anthropic_key") 
            print("   - TOGETHER_API_KEY=your_together_key")
            print("2. Go to Admin Settings → LLM Analysis to add models")
            print("3. Analyze conversations using session IDs")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise

if __name__ == '__main__':
    create_llm_tables()