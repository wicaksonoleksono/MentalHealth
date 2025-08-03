# app/services/llm_analysis.py
import json
import re
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from app import db
from app.models.llm_analysis import LLMModel, LLMAnalysisResult, AnalysisConfiguration
from app.models.assessment import Assessment, OpenQuestionResponse

load_dotenv()

class LLMAnalysisService:
    """Service for managing multi-LLM analysis of chat conversations"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    
    
    def add_llm_model(self, model_name, provider="openai"):
        """Add a new LLM model for analysis"""
        if provider != 'openai':
            raise ValueError("Only 'openai' provider is supported.")

        api_key_configured = bool(self.openai_api_key)
        
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
        """Call the appropriate LLM API"""
        if provider == 'openai':
            return self._call_openai(model_name, prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _call_openai(self, model_name, prompt):
        """Call OpenAI API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    
    
    def parse_json_response(self, raw_response):
        """Parse JSON response from LLM, handling various formats"""
        # Remove markdown code blocks if present
        cleaned_response = re.sub(r'```json\s*', '', raw_response)
        cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()
        
        try:
            # Try direct JSON parsing
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Try to extract JSON from text
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
                start_time = time.time()
                
                # Build full prompt
                full_prompt = f"{formatted_chat}\n\n{config.instruction_prompt}\n\n{config.format_prompt}"
                
                # Call LLM API
                raw_response = self.call_llm_api(model.name, model.provider, full_prompt)
                
                # Parse response
                parsed_results = self.parse_json_response(raw_response)
                
                processing_time = int((time.time() - start_time) * 1000)
                
                # Save result
                analysis_result = LLMAnalysisResult(
                    session_id=session_id,
                    llm_model_id=model.id,
                    chat_history=formatted_chat,
                    analysis_prompt=config.instruction_prompt,
                    format_prompt=config.format_prompt,
                    raw_response=raw_response,
                    analysis_status='completed',
                    processing_time_ms=processing_time,
                    completed_at=datetime.utcnow()
                )
                analysis_result.set_parsed_results(parsed_results)
                
                db.session.add(analysis_result)
                results.append(analysis_result)
                
            except Exception as e:
                # Save error result
                analysis_result = LLMAnalysisResult(
                    session_id=session_id,
                    llm_model_id=model.id,
                    chat_history=formatted_chat,
                    analysis_prompt=config.instruction_prompt if config else "",
                    format_prompt=config.format_prompt if config else "",
                    raw_response="",
                    analysis_status='failed',
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
                db.session.add(analysis_result)
                results.append(analysis_result)
        
        db.session.commit()
        return results
    
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