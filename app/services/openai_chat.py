# app/services/openai_chat.py - Fixed Implementation
import asyncio
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
        
        settings['max_exchanges'] = 5
        settings['enable_followup'] = True
        settings['response_style'] = 'empathetic'
        
        return settings
    
    def create_chat_session(self, assessment_session_id, user_id):
        """Initialize chat session with system prompt."""
        settings = self.get_chat_settings()
        
        system_prompt = settings['openquestion_prompt']
        context_addon = f"""

Context: This is part of a mental health assessment. The user is participating in an open-ended conversation portion. 
Be supportive, empathetic, and ask thoughtful follow-up questions to understand their mental state.
Keep responses natural and conversational. Aim for 1-3 sentences per response.
        """
        
        full_system_prompt = system_prompt + context_addon
        
        chat_session = {
            'system_prompt': full_system_prompt,
            'messages': [{'type': 'system', 'content': full_system_prompt}],
            'settings': settings,
            'exchange_count': 0,
            'started_at': datetime.utcnow().isoformat()
        }
        
        return chat_session
    
    async def stream_response_chunks(self, chat_session, user_message):
        """Stream response chunks for real-time display."""
        langchain_messages = []
        for msg in chat_session['messages']:
            if msg['type'] == 'system':
                langchain_messages.append(SystemMessage(content=msg['content']))
            elif msg['type'] == 'human':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                langchain_messages.append(AIMessage(content=msg['content']))
        
        langchain_messages.append(HumanMessage(content=user_message))
        
        async for chunk in self.llm.astream(langchain_messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    
    async def generate_streaming_response_async(self, chat_session, user_message):
        """Generate async full response from OpenAI."""
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
        async for chunk in self.llm.astream(langchain_messages):
            if hasattr(chunk, 'content') and chunk.content:
                response_chunks.append(chunk.content)
        
        full_response = ''.join(response_chunks)
        chat_session['messages'].append({'type': 'human', 'content': user_message})
        chat_session['messages'].append({'type': 'ai', 'content': full_response})
        chat_session['exchange_count'] += 1
        
        return full_response
    
    def generate_streaming_response(self, chat_session, user_message):
        """Sync wrapper for streaming response."""
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
        chat_session['messages'].append({'type': 'human', 'content': user_message})
        chat_session['messages'].append({'type': 'ai', 'content': full_response})
        chat_session['exchange_count'] += 1
    
    def save_chat_exchange(self, assessment_session_id, user_id, user_message, bot_response, response_time_ms=None):
        """Save chat exchange to database."""
        assessment = Assessment.query.filter_by(
            session_id=assessment_session_id,
            user_id=user_id
        ).first()
        
        if not assessment:
            raise Exception(f"Assessment session not found: {assessment_session_id}")
        
        user_response = OpenQuestionResponse(
            assessment_id=assessment.id,
            question_text="User Message",
            response_text=user_message,
            response_time_ms=response_time_ms
        )
        db.session.add(user_response)
        
        bot_response_record = OpenQuestionResponse(
            assessment_id=assessment.id,
            question_text="Bot Response", 
            response_text=bot_response,
            response_time_ms=None
        )
        db.session.add(bot_response_record)
        
        db.session.commit()
        return assessment
    
    def should_continue_chat(self, chat_session):
        """Determine if chat should continue based on settings."""
        settings = chat_session['settings']
        
        if chat_session['exchange_count'] >= settings['max_exchanges']:
            return False, "Thank you for sharing. That completes the open questions portion of the assessment."
        
        return True, None