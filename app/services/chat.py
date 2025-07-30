# app/services/chat_service.py
from flask import current_app
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ChatMessageHistory

from app.models.assessment import ChatMessage
from app import db
class ChatService:
    def __init__(self):
        api_key = current_app.config['OPENAI_API_KEY']
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured.")
        system_prompt = (
            "You are a gentle and empathetic assistant for a mental health assessment. "
            "Your goal is to make the user feel comfortable and encourage them to share. "
            "Listen carefully, be patient, and ask open-ended follow-up questions. "
            "Never give medical advice, diagnoses, or judgments. Keep your responses concise."
        )
        self.llm = ChatOpenAI(api_key=api_key, model="gpt-4o")
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()
    def _load_history(self, assessment_session_id: str) -> ChatMessageHistory:
        """Loads conversation history from the database for a given session."""
        db_messages = ChatMessage.query.filter_by(
            assessment_session_id=assessment_session_id
        ).order_by(ChatMessage.timestamp).all()
        history = ChatMessageHistory()
        for msg in db_messages:
            if msg.sender_type == 'user':
                history.add_user_message(msg.message)
            else:
                history.add_ai_message(msg.message)
        return history
    def _save_message(self, assessment_session_id: str, user_id: int, sender_type: str, message: str):
        chat_message = ChatMessage(
            assessment_session_id=assessment_session_id,
            user_id=user_id,
            sender_type=sender_type,
            message=message
        )
        db.session.add(chat_message)
        db.session.commit()

    def get_response(self, user_id: int, assessment_session_id: str, user_message: str) -> str:
        """
        Main method to get a bot response. It handles loading history,
        saving messages, and invoking the LLM chain.
        """
        # 1. Save the user's incoming message to the DB
        self._save_message(assessment_session_id, user_id, 'user', user_message)

        # 2. Load the full conversation history
        history = self._load_history(assessment_session_id)

        # 3. Invoke the chain with the history to get the bot's response
        bot_response = self.chain.invoke({
            "history": history.messages,
            "input": user_message
        })

        # 4. Save the bot's response to the DB
        self._save_message(assessment_session_id, user_id, 'bot', bot_response)
        
        return bot_response