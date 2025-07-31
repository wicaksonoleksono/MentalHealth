# app/services/openai_chat.py
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app import db
from app.models.settings import AppSetting
from app.models.assessment import Assessment, OpenQuestionResponse
from app.services.assesment import AssessmentService

from dotenv import load_dotenv
load_dotenv()
class OpenAIChatService:
    def __init__(self):
        # Initialize OpenAI model
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano-2025-04-14",  # or gpt-4 if you prefer
            temperature=0.1,
            streaming=True,
        )
    
    @staticmethod
    def get_chat_settings():
        """Load chat settings from database."""
        try:
            settings = {}
            
            # Get preprompt from settings - REQUIRED
            preprompt_setting = AppSetting.query.filter_by(key='openquestion_prompt').first()
            if not preprompt_setting:
                raise ValueError("Missing required setting: openquestion_prompt")
            settings['preprompt'] = preprompt_setting.value
            
            # Get instructions - REQUIRED
            instructions_setting = AppSetting.query.filter_by(key='openquestion_instructions').first()
            if not instructions_setting:
                raise ValueError("Missing required setting: openquestion_instructions")
            settings['instructions'] = instructions_setting.value
            
            # Chat behavior settings (you can add these to admin panel later)
            settings['max_exchanges'] = 5  # Maximum back-and-forth exchanges
            settings['enable_followup'] = True
            settings['response_style'] = 'empathetic'
            
            return settings
            
        except Exception as e:
            raise e
    
    def create_chat_session(self, assessment_session_id, user_id):
        """Initialize chat session with system prompt."""
        try:
            settings = self.get_chat_settings()
            
            # Create system message from admin's preprompt
            system_prompt = settings['preprompt']
            
            # Add context about the assessment
            context_addon = f"""
            
Context: This is part of a mental health assessment. The user is participating in an open-ended conversation portion. 
Be supportive, empathetic, and ask thoughtful follow-up questions to understand their mental state.
Keep responses natural and conversational. Aim for 1-3 sentences per response.
            """
            
            full_system_prompt = system_prompt + context_addon
            
            chat_session = {
                'system_prompt': full_system_prompt,
                'messages': [{'type': 'system', 'content': full_system_prompt}],  # Store as dict, not LangChain object
                'settings': settings,
                'exchange_count': 0,
                'started_at': datetime.utcnow().isoformat()
            }
            
            return chat_session
            
        except Exception as e:
            raise e
    
    def generate_streaming_response(self, chat_session, user_message):
        """Generate streaming response from OpenAI."""
        try:
            # Convert stored message dicts back to LangChain objects
            langchain_messages = []
            for msg in chat_session['messages']:
                if msg['type'] == 'system':
                    langchain_messages.append(SystemMessage(content=msg['content']))
                elif msg['type'] == 'human':
                    langchain_messages.append(HumanMessage(content=msg['content']))
                elif msg['type'] == 'ai':
                    from langchain.schema import AIMessage
                    langchain_messages.append(AIMessage(content=msg['content']))
            
            # Add current user message
            langchain_messages.append(HumanMessage(content=user_message))
            
            # Generate streaming response
            response_chunks = []
            for chunk in self.llm.stream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    response_chunks.append(chunk.content)
                    yield chunk.content  # Stream to frontend
            
            # Combine full response
            full_response = ''.join(response_chunks)
            
            # Add messages to session as dicts (JSON serializable)
            chat_session['messages'].append({'type': 'human', 'content': user_message})
            chat_session['messages'].append({'type': 'ai', 'content': full_response})
            chat_session['exchange_count'] += 1
            
            return full_response
            
        except Exception as e:
            raise e
    
    def save_chat_exchange(self, assessment_session_id, user_id, user_message, bot_response, response_time_ms=None):
        """Save chat exchange to database."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=assessment_session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Save user message
            user_response = OpenQuestionResponse(
                assessment_id=assessment.id,
                question_text="User Message",
                response_text=user_message,
                response_time_ms=response_time_ms
            )
            db.session.add(user_response)
            
            # Save bot response
            bot_response_record = OpenQuestionResponse(
                assessment_id=assessment.id,
                question_text="Bot Response",
                response_text=bot_response,
                response_time_ms=None  # Bot response time not tracked
            )
            db.session.add(bot_response_record)
            
            db.session.commit()
            return assessment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def should_continue_chat(self, chat_session):
        """Determine if chat should continue based on settings."""
        settings = chat_session['settings']
        
        # Check exchange limit
        if chat_session['exchange_count'] >= settings['max_exchanges']:
            return False, "Thank you for sharing. That completes the open questions portion of the assessment."
        
        return True, None
    
    def get_chat_summary(self, assessment_session_id, user_id):
        """Get summary of chat conversation."""
        try:
            assessment = Assessment.query.filter_by(
                session_id=assessment_session_id,
                user_id=user_id
            ).first()
            
            if not assessment:
                raise ValueError("Assessment session not found")
            
            # Get all chat responses
            responses = OpenQuestionResponse.query.filter_by(assessment_id=assessment.id).all()
            
            # Separate user and bot messages
            user_messages = [r for r in responses if r.question_text == "User Message"]
            bot_messages = [r for r in responses if r.question_text == "Bot Response"]
            
            summary = {
                'total_exchanges': len(user_messages),
                'user_messages': [r.response_text for r in user_messages],
                'bot_responses': [r.response_text for r in bot_messages],
                'conversation_flow': []
            }
            
            # Create conversation flow
            for i, user_msg in enumerate(user_messages):
                summary['conversation_flow'].append({
                    'type': 'user',
                    'message': user_msg.response_text,
                    'timestamp': user_msg.created_at
                })
                
                if i < len(bot_messages):
                    summary['conversation_flow'].append({
                        'type': 'bot',
                        'message': bot_messages[i].response_text,
                        'timestamp': bot_messages[i].created_at
                    })
            
            return summary
            
        except Exception as e:
            raise e