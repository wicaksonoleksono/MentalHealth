# app/services/openai_chat.py
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage
from app import db
from app.models.settings import AppSetting, SettingsKey
from app.models.assessment import Assessment, OpenQuestionResponse
from app.services.settings import SettingsService
load_dotenv()
class OpenAIChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            streaming=True
        )
        # Initialize conversation memory for context preservation
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
    
    @staticmethod
    def get_chat_settings():
        """Load chat settings from database using SettingsService for consistency."""
        from app.models.settings import AppSetting
        
        # Get settings directly from database
        openquestion_prompt = AppSetting.query.filter_by(key='openquestion_prompt').first()
        openquestion_instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()
        
        settings = {
            'openquestion_prompt': openquestion_prompt.value if openquestion_prompt else '',
            'instructions': openquestion_instructions.value if openquestion_instructions else '',
            'enable_followup': True,
            'response_style': 'empathetic'
        }
        
        # Don't raise exceptions, just use defaults if missing
        if not settings['openquestion_prompt']:
            settings['openquestion_prompt'] = "You are a compassionate mental health assessment assistant. Help the user express their thoughts and feelings."
        
        if not settings['instructions']:
            settings['instructions'] = "Please share your thoughts and feelings openly. This is a safe space."
        
        return settings
    
    def create_chat_session(self, assessment_session_id, user_id):
        """Create a new chat session with LangChain conversation memory."""
        settings = self.get_chat_settings()
        system_prompt = settings['openquestion_prompt']
        
        # Use default if system prompt is empty
        if not system_prompt or system_prompt.strip() == '':
            system_prompt = "You are a compassionate mental health assessment assistant. Help the user express their thoughts and feelings."
        
        # Create fresh memory for this session
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Initialize with system message
        system_message = SystemMessage(content=system_prompt)
        
        # Store serializable session data (no LangChain objects)
        chat_session = {
            'system_prompt': system_prompt,
            'message_history': [{'type': 'system', 'content': system_prompt}],  # Serializable message history
            'conversation_history': [],  # Store for display/logging
            'settings': settings,
            'exchange_count': 0,
            'started_at': datetime.utcnow().isoformat(),
            'assessment_session_id': assessment_session_id,
            'user_id': user_id
        }
        
        # Add system message to conversation history for logging
        chat_session['conversation_history'].append({
            'type': 'system', 
            'content': system_prompt, 
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return chat_session
    
    def generate_streaming_response(self, chat_session, user_message):
        """Generate streaming response using LangChain conversation chain with proper context."""
        current_time = datetime.utcnow().isoformat()
        
        # Add user message to serializable message history
        chat_session['message_history'].append({'type': 'human', 'content': user_message})
        
        # Add to conversation history for logging
        chat_session['conversation_history'].append({
            'type': 'human', 
            'content': user_message,
            'timestamp': current_time
        })
        
        # Rebuild LangChain messages from serializable history
        langchain_messages = []
        for msg in chat_session['message_history']:
            if msg['type'] == 'system':
                langchain_messages.append(SystemMessage(content=msg['content']))
            elif msg['type'] == 'human':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                langchain_messages.append(AIMessage(content=msg['content']))
        
        # Process messages for streaming
        
        # Use the full conversation context for streaming
        response_chunks = []
        for chunk in self.llm.stream(langchain_messages):
            if hasattr(chunk, 'content') and chunk.content:
                response_chunks.append(chunk.content)
                yield chunk.content
        
        # Build full response
        full_response = ''.join(response_chunks)
        
        # Add AI response to serializable message history
        chat_session['message_history'].append({'type': 'ai', 'content': full_response})
        
        # Add to conversation history for logging
        chat_session['conversation_history'].append({
            'type': 'ai', 
            'content': full_response,
            'timestamp': current_time
        })
        
        # Update exchange count
        chat_session['exchange_count'] += 1
        
        # Update memory with the exchange
        self.memory.chat_memory.add_user_message(user_message)
        self.memory.chat_memory.add_ai_message(full_response)
    
    def save_conversation(self, assessment_session_id, user_id, conversation_data):
        """Save entire LangChain conversation with proper context preservation."""
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise Exception(f"Assessment session not found: {assessment_session_id}")
        
        # Calculate session duration
        session_duration_seconds = None
        if 'started_at' in conversation_data:
            try:
                start_time = datetime.fromisoformat(conversation_data['started_at'])
                end_time = datetime.utcnow()
                session_duration_seconds = (end_time - start_time).total_seconds()
            except:
                pass
        
        # Get current settings to save with conversation
        current_chat_settings = self.get_chat_settings()
        current_recording_settings = None
        try:
            from app.services.settings import SettingsService
            current_recording_settings = SettingsService.get_recording_config()
        except:
            pass
        
        # Prepare comprehensive conversation metadata
        conversation_metadata = {
            'system_prompt': conversation_data.get('system_prompt', ''),
            'settings_used': conversation_data.get('settings', {}),
            'conversation_history': conversation_data.get('conversation_history', []),
            'message_history': conversation_data.get('message_history', []),
            'total_exchanges': conversation_data.get('exchange_count', 0),
            'session_duration_seconds': session_duration_seconds,
            'started_at': conversation_data.get('started_at'),
            'completed_at': datetime.utcnow().isoformat(),
            'current_settings_snapshot': {
                'chat_settings': current_chat_settings,
                'recording_settings': current_recording_settings,
                'assessment_order': assessment.assessment_order if hasattr(assessment, 'assessment_order') else None
            },
            'langchain_context': {
                'message_count': len(conversation_data.get('message_history', [])),
                'has_system_prompt': bool(conversation_data.get('system_prompt')),
                'memory_preserved': True
            }
        }
        
        # Save the complete conversation as structured JSON
        conversation_record = OpenQuestionResponse(
            assessment_id=assessment.id,
            question_text="Complete LangChain Conversation",
            response_text=json.dumps(conversation_metadata, indent=2, ensure_ascii=False),
            response_time_ms=int(session_duration_seconds * 1000) if session_duration_seconds else None
        )
        db.session.add(conversation_record)
        
        # Also save individual exchanges for easier analysis with timestamps
        for i, msg in enumerate(conversation_data.get('conversation_history', [])):
            if msg['type'] in ['human', 'ai']:
                # Parse timestamp from conversation history
                msg_timestamp = None
                if 'timestamp' in msg:
                    try:
                        msg_timestamp = datetime.fromisoformat(msg['timestamp'])
                    except (ValueError, TypeError):
                        pass
                
                exchange_data = {
                    'assessment_id': assessment.id,
                    'question_text': f"Exchange {i//2 + 1} - {msg['type'].title()}",
                    'response_text': msg['content'],
                    'response_time_ms': None
                }
                
                if msg_timestamp:
                    exchange_data['created_at'] = msg_timestamp
                
                exchange_record = OpenQuestionResponse(**exchange_data)
                db.session.add(exchange_record)
        
        db.session.commit()
        return assessment