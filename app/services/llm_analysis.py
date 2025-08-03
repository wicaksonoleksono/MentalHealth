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
  }, ...
}
"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    
    
    def _validate_openai_model(self, model_name):
        """Comprehensive OpenAI model validation using industry standards"""
        validation_result = {
            'valid': False,
            'error': None,
            'details': {
                'model_exists': False,
                'api_accessible': False,
                'langchain_compatible': False,
                'response_format_valid': False
            }
        }
        
        try:
            # Step 1: Check if model exists in OpenAI's official model list
            known_models = {
                'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-4-32k',
                'gpt-3.5-turbo', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-instruct',
                'text-davinci-003', 'text-davinci-002', 'text-curie-001', 'text-babbage-001'
            }
            
            if model_name not in known_models:
                # Try to get current model list from OpenAI API
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=self.openai_api_key)
                    models_response = client.models.list()
                    available_models = {model.id for model in models_response.data}
                    
                    if model_name not in available_models:
                        validation_result['error'] = f"Model '{model_name}' not found in OpenAI's available models"
                        return validation_result
                    
                except Exception as e:
                    # If we can't fetch model list, warn but continue with other validation
                    pass
            
            validation_result['details']['model_exists'] = True
            
            # Step 2: Test LangChain compatibility and API access
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import HumanMessage
                
                test_llm = ChatOpenAI(
                    model=model_name,
                    temperature=0.0,
                    openai_api_key=self.openai_api_key,
                    max_tokens=10,
                    timeout=30,
                    max_retries=1
                )
                
                # Test with minimal request to validate access and compatibility
                test_message = HumanMessage(content="Test")
                response = test_llm.invoke([test_message])
                
                validation_result['details']['langchain_compatible'] = True
                validation_result['details']['api_accessible'] = True
                
                # Step 3: Validate response format
                if hasattr(response, 'content') and isinstance(response.content, str):
                    validation_result['details']['response_format_valid'] = True
                    validation_result['valid'] = True
                else:
                    validation_result['error'] = "Model response format is invalid"
                    return validation_result
                    
            except ImportError as e:
                validation_result['error'] = f"LangChain not properly installed: {str(e)}"
                return validation_result
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Specific error handling for common issues
                if "model_not_found" in error_str or "does not exist" in error_str:
                    validation_result['error'] = f"Model '{model_name}' does not exist or you don't have access to it"
                elif "rate_limit" in error_str:
                    validation_result['error'] = "Rate limit exceeded. Please try again later"
                elif "api_key" in error_str or "unauthorized" in error_str:
                    validation_result['error'] = "Invalid or insufficient API key permissions"
                elif "quota" in error_str:
                    validation_result['error'] = "API quota exceeded. Check your OpenAI billing"
                elif "timeout" in error_str:
                    validation_result['error'] = "Request timeout. Model may be unavailable"
                else:
                    validation_result['error'] = f"Model validation failed: {str(e)}"
                
                return validation_result
                
        except Exception as e:
            validation_result['error'] = f"Validation error: {str(e)}"
            return validation_result
        
        return validation_result
    
    def add_llm_model(self, model_name, provider="openai"):
        """Add a new LLM model with comprehensive validation using industry standards"""
        # Input validation
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Model name must be a non-empty string")
        
        model_name = model_name.strip()
        if not model_name:
            raise ValueError("Model name cannot be empty")
            
        if provider != 'openai':
            raise ValueError("Only 'openai' provider is supported")
        
        # Check for duplicates first
        existing_model = LLMModel.query.filter_by(name=model_name, provider=provider).first()
        if existing_model:
            raise ValueError(f"Model '{model_name}' already exists")
        
        # API key validation
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in environment")
        
        # Comprehensive model validation
        logger.info(f"Validating model '{model_name}' with OpenAI API...")
        validation_result = self._validate_openai_model(model_name)
        
        if not validation_result['valid']:
            logger.error(f"Model validation failed for '{model_name}': {validation_result['error']}")
            raise ValueError(validation_result['error'])
        
        # Log successful validation details
        details = validation_result['details']
        logger.info(f"Model '{model_name}' validation successful - "
                   f"Exists: {details['model_exists']}, "
                   f"API Access: {details['api_accessible']}, "
                   f"LangChain Compatible: {details['langchain_compatible']}, "
                   f"Response Valid: {details['response_format_valid']}")
        
        # Create and save model if all validation passes
        try:
            llm_model = LLMModel(
                name=model_name,
                provider=provider,
                api_key_configured=True,  # We know it's configured if validation passed
                is_active=True
            )
            
            db.session.add(llm_model)
            db.session.commit()
            
            logger.info(f"Successfully added model '{model_name}' to database")
            return llm_model
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save model '{model_name}' to database: {str(e)}")
            raise ValueError(f"Failed to save model to database: {str(e)}")
    
    def validate_model_without_saving(self, model_name, provider="openai"):
        """Validate a model without saving to database (for testing purposes)"""
        if provider != 'openai':
            raise ValueError("Only 'openai' provider is supported")
            
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
            
        return self._validate_openai_model(model_name)
    
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
                        assessment_id=assessment.id,
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
                        assessment_id=assessment.id,
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