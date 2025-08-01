# app/services/openai_chat.py
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app import db
from app.models.settings import AppSetting
from app.models.assessment import Assessment, OpenQuestionResponse
load_dotenv()
class OpenAIChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            streaming=True
        )
    
    @staticmethod
    def get_chat_settings():
        """Load chat settings from database."""
        settings = {}
        
        preprompt_setting = AppSetting.query.filter_by(key='openquestion_prompt').first()
        if not preprompt_setting:
            raise Exception(f"Missing required setting: openquestion_prompt. Run: flask add-chat-settings")
        settings['openquestion_prompt'] = preprompt_setting.value
        
        instructions_setting = AppSetting.query.filter_by(key='openquestion_instructions').first()
        if not instructions_setting:
            raise Exception(f"Missing required setting: openquestion_instructions. Run: flask add-chat-settings")
        settings['instructions'] = instructions_setting.value
        
        settings['enable_followup'] = True
        settings['response_style'] = 'empathetic'
        
        return settings
    
    def create_chat_session(self, assessment_session_id, user_id):
        settings = self.get_chat_settings()
        system_prompt = settings['openquestion_prompt']
        full_system_prompt = system_prompt
        chat_session = {
            'system_prompt': full_system_prompt,
            'messages': [{'type': 'system', 'content': full_system_prompt, 'timestamp': datetime.utcnow().isoformat()}],
            'settings': settings,
            'exchange_count': 0,
            'started_at': datetime.utcnow().isoformat()
        }
        return chat_session
    
    def generate_streaming_response(self, chat_session, user_message):
        """Generate streaming response and update chat session."""
        langchain_messages = []
        for msg in chat_session['messages']:
            if msg['type'] == 'system':
                langchain_messages.append(SystemMessage(content=msg['content']))
            elif msg['type'] == 'human':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                langchain_messages.append(AIMessage(content=msg['content']))
        langchain_messages.append(HumanMessage(content=user_message))
        
        response_chunks = []
        for chunk in self.llm.stream(langchain_messages):
            if hasattr(chunk, 'content') and chunk.content:
                response_chunks.append(chunk.content)
                yield chunk.content
        
        full_response = ''.join(response_chunks)
        current_time = datetime.utcnow().isoformat()
        
        # Add to chat session with timestamps
        chat_session['messages'].append({
            'type': 'human', 
            'content': user_message,
            'timestamp': current_time
        })
        chat_session['messages'].append({
            'type': 'ai', 
            'content': full_response,
            'timestamp': current_time
        })
        chat_session['exchange_count'] += 1
    
    def save_conversation(self, assessment_session_id, user_id, conversation_data):
        """Save entire conversation as raw JSON with proper timestamping."""
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise Exception(f"Assessment session not found: {assessment_session_id}")
        
        # Prepare conversation metadata
        conversation_metadata = {
            'conversation_data': conversation_data,
            'total_exchanges': conversation_data.get('exchange_count', 0),
            'session_duration_seconds': None,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Calculate session duration if possible
        if 'started_at' in conversation_data:
            try:
                start_time = datetime.fromisoformat(conversation_data['started_at'])
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                conversation_metadata['session_duration_seconds'] = duration
            except:
                pass
        
        # Save conversation as single record with JSON data
        conversation_record = OpenQuestionResponse(
            assessment_id=assessment.id,
            question_text="Full Conversation Log",
            response_text=json.dumps(conversation_metadata, indent=2),
            response_time_ms=None
        )
        db.session.add(conversation_record)
        db.session.commit()
        return assessment