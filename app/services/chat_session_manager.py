# app/services/chat_session_manager.py
from datetime import datetime
from typing import Dict, Optional
import threading
from app.services.openai_chat import OpenAIChatService

class ChatSessionManager:
    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._openai_service = OpenAIChatService()
        self._lock = threading.RLock()
    def create_session(self, session_id: str, assessment_session_id: str, user_id: int) -> str:
        with self._lock:
            chat_session = self._openai_service.create_chat_session(assessment_session_id, user_id)
            session_token = f"chat_{session_id}_{user_id}"
            self._sessions[session_token] = chat_session
            return session_token
    def get_session(self, session_token: str) -> Optional[dict]:
        with self._lock:
            return self._sessions.get(session_token)
    def update_session(self, session_token: str, user_message: str, ai_response: str):
        with self._lock:
            session = self._sessions.get(session_token)
            if not session:
                return False
            current_time = datetime.utcnow().isoformat()
            session['message_history'].append({'type': 'human', 'content': user_message})
            session['message_history'].append({'type': 'ai', 'content': ai_response})
            session['conversation_history'].append({
                'type': 'human', 
                'content': user_message,
                'timestamp': current_time
            })
            session['conversation_history'].append({
                'type': 'ai', 
                'content': ai_response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            session['exchange_count'] = session.get('exchange_count', 0) + 1
            
            return True
    
    def add_user_message(self, session_token: str, user_message: str):
        """Add user message to session (before streaming)."""
        with self._lock:
            session = self._sessions.get(session_token)
            if not session:
                return False
            
            current_time = datetime.utcnow().isoformat()
            session['message_history'].append({'type': 'human', 'content': user_message})
            session['conversation_history'].append({
                'type': 'human', 
                'content': user_message,
                'timestamp': current_time
            })
            return True
    
    def add_ai_response(self, session_token: str, ai_response: str):
        """Add AI response to session (after streaming)."""
        with self._lock:
            session = self._sessions.get(session_token)
            if not session:
                return False
            
            session['message_history'].append({'type': 'ai', 'content': ai_response})
            session['conversation_history'].append({
                'type': 'ai', 
                'content': ai_response,
                'timestamp': datetime.utcnow().isoformat()
            })
            session['exchange_count'] = session.get('exchange_count', 0) + 1
            return True
    
    def delete_session(self, session_token: str):
        """Delete chat session."""
        with self._lock:
            if session_token in self._sessions:
                del self._sessions[session_token]
    
    def get_session_stats(self) -> dict:
        """Get session manager statistics."""
        with self._lock:
            return {
                'total_sessions': len(self._sessions),
                'session_tokens': list(self._sessions.keys())
            }
    
    def stream_response(self, session_token: str, user_message: str):
        """Stream AI response using session context."""
        session = self.get_session(session_token)
        if not session:
            raise ValueError(f"Session {session_token} not found")
        return self._openai_service.generate_streaming_response(session, user_message)
# Lazy initialization to avoid issues with Gunicorn/multi-process deployment
_chat_session_manager = None

def get_chat_session_manager():
    """Get the chat session manager instance (lazy initialization)"""
    global _chat_session_manager
    if _chat_session_manager is None:
        _chat_session_manager = ChatSessionManager()
    return _chat_session_manager