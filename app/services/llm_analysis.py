# app/services/llm_analysis.py
import json
import re
import time
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from app import db
from app.models.llm_analysis import LLMModel, LLMAnalysisResult, AnalysisConfiguration
from app.models.assessment import Assessment, OpenQuestionResponse

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LLMAnalysisService:
    """Service for managing multi-LLM analysis of chat conversations"""
    
    # Hardcoded format for consistent parsing
    ANALYSIS_FORMAT = """Gunakan format JSON berikut:
{
  "indicator_1": {
    "penjelasan": "penjelasan untuk indikator 1",
    "skor": 0
  },
  "indicator_2": {
    "penjelasan": "penjelasan untuk indikator 2", 
    "skor": 0
  },
  "indicator_3": {
    "penjelasan": "penjelasan untuk indikator 3",
    "skor": 0
  },
  "indicator_4": {
    "penjelasan": "penjelasan untuk indikator 4",
    "skor": 0
  },
  "indicator_5": {
    "penjelasan": "penjelasan untuk indikator 5",
    "skor": 0
  },
  "indicator_6": {
    "penjelasan": "penjelasan untuk indikator 6",
    "skor": 0
  },
  "indicator_7": {
    "penjelasan": "penjelasan untuk indikator 7",
    "skor": 0
  },
  "indicator_8": {
    "penjelasan": "penjelasan untuk indikator 8",
    "skor": 0
  },
  "indicator_9": {
    "penjelasan": "penjelasan untuk indikator 9",
    "skor": 0
  },
  "indicator_10": {
    "penjelasan": "penjelasan untuk indikator 10",
    "skor": 0
  },
  "indicator_11": {
    "penjelasan": "penjelasan untuk indikator 11",
    "skor": 0
  }
}

Skor menggunakan skala 0-3:
0: Tidak Ada Indikasi Jelas
1: Indikasi Ringan  
2: Indikasi Sedang
3: Indikasi Kuat"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    
    
    def add_llm_model(self, model_name, provider="openai"):
        """Add a new LLM model for analysis with LangChain support"""
        if provider != 'openai':
            raise ValueError("Only 'openai' provider is supported.")

        # Check if API key is configured
        api_key_configured = bool(self.openai_api_key)
        if not api_key_configured:
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in environment.")
        
        # Test if LangChain or basic OpenAI is available
        try:
            from langchain_openai import ChatOpenAI
            # Test the model with a simple call
            test_llm = ChatOpenAI(
                model=model_name,
                temperature=0.0,
                openai_api_key=self.openai_api_key,
                max_tokens=10
            )
            # This will validate the model exists
            test_llm.invoke([{"role": "user", "content": "test"}])
            
        except ImportError:
            # Fallback to basic OpenAI for validation
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                # Test if model exists
                client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
            except Exception as e:
                raise ValueError(f"Model validation failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"Model validation failed: {str(e)}")
        
        # Check if model already exists
        existing_model = LLMModel.query.filter_by(name=model_name, provider=provider).first()
        if existing_model:
            raise ValueError(f"Model {model_name} already exists")
        
        # Create new model
        llm_model = LLMModel(
            name=model_name,
            provider=provider,
            api_key_configured=api_key_configured
        )
        db.session.add(llm_model)
        db.session.commit()
        return llm_model
    
    def remove_llm_model(self, model_name):
        """Remove an LLM model"""
        model = LLMModel.query.filter_by(name=model_name).first()
        if not model:
            raise ValueError(f"Model {model_name} not found")
        
        db.session.delete(model)
        db.session.commit()
        return True
    
    def get_active_models(self):
        """Get all active LLM models"""
        return LLMModel.query.filter_by(is_active=True).all()
    
    def get_available_providers(self):
        """Get available LLM providers with LangChain support check"""
        providers = []
        
        # Check OpenAI availability
        if self.openai_api_key:
            try:
                # Try to import LangChain OpenAI
                from langchain_openai import ChatOpenAI
                providers.append({
                    'name': 'openai', 
                    'display_name': 'OpenAI (LangChain)',
                    'available': True,
                    'backend': 'langchain'
                })
            except ImportError:
                # Fallback to basic OpenAI
                try:
                    from openai import OpenAI
                    providers.append({
                        'name': 'openai',
                        'display_name': 'OpenAI (Basic)',
                        'available': True,
                        'backend': 'basic'
                    })
                except ImportError:
                    providers.append({
                        'name': 'openai',
                        'display_name': 'OpenAI (Not Available)',
                        'available': False,
                        'backend': 'none'
                    })
        else:
            providers.append({
                'name': 'openai',
                'display_name': 'OpenAI (No API Key)',
                'available': False,
                'backend': 'none'
            })
        
        return providers
    
    def get_model_names(self):
        """Get list of active model names for API"""
        models = self.get_active_models()
        return [model.name for model in models]
    
    def get_chat_history_for_session(self, session_id):
        """Extract chat history from assessment session"""
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            raise ValueError(f"Assessment session {session_id} not found")
        
        # Get open question responses (conversation data)
        responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).all()
        
        chat_history = []
        for response in responses:
            if response.question_text == "Complete LangChain Conversation":
                # Parse the complete conversation JSON
                try:
                    conversation_data = json.loads(response.response_text)
                    if 'conversation_history' in conversation_data:
                        for msg in conversation_data['conversation_history']:
                            if msg['type'] in ['human', 'ai']:
                                chat_history.append({
                                    'type': msg['type'],
                                    'content': msg['content'],
                                    'timestamp': msg.get('timestamp', '')
                                })
                except json.JSONDecodeError:
                    continue
        
        return chat_history
    
    def format_chat_for_analysis(self, chat_history):
        """Format chat history for LLM analysis"""
        formatted_chat = ""
        for msg in chat_history:
            if msg['type'] == 'human':
                formatted_chat += f"Teman: {msg['content']}\n\n"
            elif msg['type'] == 'ai':
                formatted_chat += f"Anisa: {msg['content']}\n\n"
        return formatted_chat.strip()
    
    def call_llm_api(self, model_name, provider, prompt):
        if provider == 'openai':
            return self._call_openai(model_name, prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _call_openai(self, model_name, prompt):
        """Call OpenAI API using LangChain integration"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            
            # Initialize LangChain OpenAI client
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.0,
                openai_api_key=self.openai_api_key,
                max_retries=2,
                request_timeout=60
            )
            
            # Create message and invoke
            messages = [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            
            return response.content
            
        except ImportError:
            # Fallback to basic OpenAI client if LangChain not available
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                return response.choices[0].message.content
            except Exception as e:
                raise Exception(f"OpenAI API error (fallback): {str(e)}")
                
        except Exception as e:
            raise Exception(f"LangChain OpenAI error: {str(e)}")
    def parse_json_response(self, raw_response):
        """Parse JSON response from LLM, handling various formats"""
        cleaned_response = re.sub(r'```json\s*', '', raw_response)
        cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, cleaned_response, re.DOTALL)
            
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, return empty dict
            return {}
    
    def analyze_session(self, session_id):
        """Analyze a session with all active LLM models"""
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            raise ValueError(f"Assessment session {session_id} not found")

        assessment.llm_analysis_status = 'in_progress'
        db.session.commit()

        try:
            # Get chat history
            chat_history = self.get_chat_history_for_session(session_id)
            if not chat_history:
                raise ValueError(f"No chat history found for session {session_id}")
            
            formatted_chat = self.format_chat_for_analysis(chat_history)
            
            # Get analysis configuration
            config = AnalysisConfiguration.get_active_config()
            if not config:
                raise ValueError("No active analysis configuration found")
            
            # Get active models
            models = self.get_active_models()
            if not models:
                raise ValueError("No active LLM models configured")
            
            results = []
            
            for model in models:
                try:
                    logger.info(f"Starting analysis for session {session_id} with model {model.name}")
                    start_time = time.time()
                    
                    # Build full prompt
                    full_prompt = f"{formatted_chat}\n\n{config.instruction_prompt}\n\n{self.ANALYSIS_FORMAT}"
                    
                    # Call LLM API with enhanced error handling
                    logger.debug(f"Calling LLM API for model {model.name}")
                    raw_response = self.call_llm_api(model.name, model.provider, full_prompt)
                    
                    # Parse response
                    logger.debug(f"Parsing response from model {model.name}")
                    parsed_results = self.parse_json_response(raw_response)
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    logger.info(f"Analysis completed for model {model.name} in {processing_time}ms")
                    
                    # Save successful result
                    analysis_result = LLMAnalysisResult(
                        session_id=session_id,
                        llm_model_id=model.id,
                        chat_history=formatted_chat,
                        analysis_prompt=config.instruction_prompt,
                        format_prompt=self.ANALYSIS_FORMAT,
                        raw_response=raw_response,
                        analysis_status='completed',
                        processing_time_ms=processing_time,
                        completed_at=datetime.utcnow()
                    )
                    analysis_result.set_parsed_results(parsed_results)
                    db.session.add(analysis_result)
                    results.append(analysis_result)
                    
                except Exception as e:
                    logger.error(f"Analysis failed for model {model.name}: {str(e)}")
                    
                    # Save error result with detailed error information
                    error_msg = str(e)
                    if "rate limit" in error_msg.lower():
                        error_msg = "Rate limit exceeded. Please try again later."
                    elif "api key" in error_msg.lower():
                        error_msg = "API key issue. Please check your OpenAI configuration."
                    elif "timeout" in error_msg.lower():
                        error_msg = "Request timed out. The model may be overloaded."
                    
                    analysis_result = LLMAnalysisResult(
                        session_id=session_id,
                        llm_model_id=model.id,
                        chat_history=formatted_chat,
                        analysis_prompt=config.instruction_prompt if config else "",
                        format_prompt=self.ANALYSIS_FORMAT,
                        raw_response="",
                        analysis_status='failed',
                        error_message=error_msg,
                        completed_at=datetime.utcnow()
                    )
                    db.session.add(analysis_result)
                    results.append(analysis_result)
            
            assessment.llm_analysis_status = 'completed'
            assessment.llm_analysis_at = datetime.utcnow()
            db.session.commit()
            return results
        except Exception as e:
            assessment.llm_analysis_status = 'failed'
            db.session.commit()
            raise e
    
    def get_session_analysis_results(self, session_id):
        """Get all analysis results for a session"""
        return LLMAnalysisResult.query.filter_by(session_id=session_id).all()
    
    def update_analysis_configuration(self, instruction_prompt, format_prompt):
        """Update analysis configuration"""
        # Deactivate current config
        current_config = AnalysisConfiguration.get_active_config()
        if current_config:
            current_config.is_active = False
        
        # Create new config
        new_config = AnalysisConfiguration(
            instruction_prompt=instruction_prompt,
            format_prompt=format_prompt,
            is_active=True
        )
        db.session.add(new_config)
        db.session.commit()
        return new_config