# app/services/openai_chat.py
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.base import BaseCallbackHandler
from app import db
from app.models.settings import AppSetting, SettingsKey
from app.models.assessment import Assessment, OpenQuestionResponse
from app.services.settings import SettingsService
load_dotenv()

class StreamingHandler(BaseCallbackHandler):
    """Custom streaming handler for Server-Sent Events"""
    def __init__(self):
        self.tokens = []
        self.current_output = ""
    
    def on_llm_new_token(self, token: str, **kwargs):
        """Called when LLM generates a new token"""
        self.tokens.append(token)
        self.current_output += token
    
    def get_tokens(self):
        """Generator to yield tokens for streaming"""
        for token in self.tokens:
            yield token
    
    def reset(self):
        """Reset for new conversation"""
        self.tokens = []
        self.current_output = ""

class OpenAIChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            streaming=True
        )
        # Industry standard: RunnableWithMessageHistory
        self.chat_history = {}  # session_id -> InMemoryChatMessageHistory
        self.chain_with_history = None
    
    @staticmethod
    def get_chat_settings():
        """Load chat settings from database using SettingsService for consistency."""
        try:
            from app.models.settings import SettingsKey
            from app.services.settings import SettingsService
            
            # Use the proper SettingsService to get values
            openquestion_prompt = SettingsService.get(SettingsKey.OPENQUESTION_PROMPT)
            openquestion_instructions = SettingsService.get(SettingsKey.OPENQUESTION_INSTRUCTIONS)
            
            settings = {
                'openquestion_prompt': openquestion_prompt or '',
                'instructions': openquestion_instructions or '',
                'enable_followup': True,
                'response_style': 'empathetic'
            }
            
        except Exception as e:
            from app.models.settings import AppSetting
            openquestion_prompt = AppSetting.query.filter_by(key='openquestion_prompt').first()
            openquestion_instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()
            
            settings = {
                'openquestion_prompt': openquestion_prompt.value if openquestion_prompt else '',
                'instructions': openquestion_instructions.value if openquestion_instructions else '',
                'enable_followup': True,
                'response_style': 'empathetic'
            }
        if not settings['openquestion_prompt']:
            raise ValueError("openquestion_prompt not configured in admin settings! This is REQUIRED for research validity. Please configure it in the admin panel.")
        if not settings['instructions']:
            settings['instructions'] = "Please take your time to share your thoughts and feelings. This is a safe space where you can express yourself openly."
        return settings
    
    def create_chat_session(self, assessment_session_id, user_id):
        """Create a new chat session with industry standard RunnableWithMessageHistory."""
        settings = self.get_chat_settings()
        system_prompt = settings['openquestion_prompt']
        
        # Create session ID for this conversation
        session_id = f"{assessment_session_id}_{user_id}"
        
        # Industry standard approach: RunnableWithMessageHistory
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create the chain
        chain = prompt | self.llm
        
        # Create chat history for this session
        self.chat_history[session_id] = ChatMessageHistory()
        
        # Wrap with message history
        self.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: self.chat_history[session_id],
            input_messages_key="input",
            history_messages_key="history"
        )
        
        # Store serializable session data for Flask session
        chat_session = {
            'session_id': session_id,
            'system_prompt': system_prompt,
            'message_history': [{'type': 'system', 'content': system_prompt}],
            'conversation_history': [],
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
    
    def restore_chain_from_session(self, chat_session):
        """Restore LangChain chain and history from Flask session data."""
        session_id = chat_session['session_id']
        system_prompt = chat_session['system_prompt']
        
        # Recreate the chain if needed
        if not self.chain_with_history:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}")
            ])
            
            chain = prompt | self.llm
            
            # Ensure we have chat history for this session
            if session_id not in self.chat_history:
                self.chat_history[session_id] = ChatMessageHistory()
            
            self.chain_with_history = RunnableWithMessageHistory(
                chain,
                lambda sid: self.chat_history[sid],
                input_messages_key="input",
                history_messages_key="history"
            )
        
        # Restore conversation history to LangChain memory
        history = self.chat_history[session_id]
        history.clear()  # Clear existing to avoid duplication
        
        for msg in chat_session['message_history']:
            if msg['type'] == 'human':
                history.add_user_message(msg['content'])
            elif msg['type'] == 'ai':
                history.add_ai_message(msg['content'])
            # Skip system messages - they're in the prompt template
    
    def generate_streaming_response(self, chat_session, user_message):
        """Generate streaming response using direct LLM streaming with FULL conversation history."""
        session_id = chat_session['session_id']
        
        # Build messages manually with COMPLETE conversation context
        messages = []
        
        # Add system prompt FIRST
        system_prompt = chat_session['system_prompt']
        if not system_prompt:
            raise ValueError("🚨 CRITICAL: No system prompt found! Research context REQUIRED!")
        messages.append(SystemMessage(content=system_prompt))
        
        # Add ALL conversation history to maintain context
        for msg in chat_session['message_history']:
            if msg['type'] == 'human':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                messages.append(AIMessage(content=msg['content']))
        messages.append(HumanMessage(content=user_message))
        for chunk in self.llm.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    
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