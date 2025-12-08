"""
Conversation Manager Service - Manages conversation lifecycle and persistence
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from src.domain.entities.conversation import (
    ConversationContext, ConversationSession, ConversationMessage, MessageRole
)
from src.infrastructure.repositories.conversation_repository import ConversationRepository
from src.utilities.logger import get_logger
import json

from src.infrastructure.cache import get_cache
redis_client = get_cache()

logger = get_logger(__name__)

# Initialize repository for database persistence
_repository = ConversationRepository()

# Session storage: in-memory cache (backed by Redis for persistence)
_sessions: Dict[str, ConversationSession] = {}
SESSION_CACHE_KEY = "conversation_sessions"
SESSION_EXPIRY = 7 * 24 * 60 * 60  # 7 days in seconds


class ConversationManager:
    """Manages conversation state, history, and context"""
    
    @staticmethod
    def create_session(user_id: str) -> ConversationSession:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id
        )
        
        # Store in memory
        _sessions[session_id] = session
        
        # Persist to Redis
        ConversationManager._persist_session(session)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by ID"""
        # Try memory first
        if session_id in _sessions:
            return _sessions[session_id]
        
        # Try Redis
        session_data = ConversationManager._load_session(session_id)
        if session_data:
            _sessions[session_id] = session_data
            return session_data
        
        return None
    
    @staticmethod
    def create_conversation(
        session_id: str,
        asset_symbol: str,
        conversation_id: Optional[str] = None
    ) -> ConversationContext:
        """Create or retrieve a conversation within a session"""
        session = ConversationManager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        conversation = session.get_or_create_conversation(conversation_id, asset_symbol)
        
        # Persist to database
        _repository.save_conversation(conversation)
        
        # Persist to Redis cache
        ConversationManager._persist_session(session)
        
        logger.info(f"Created/retrieved conversation {conversation_id} for asset {asset_symbol}")
        return conversation
    
    @staticmethod
    def add_message(
        session_id: str,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Add a message to a conversation"""
        session = ConversationManager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if conversation_id not in session.conversations:
            raise ValueError(f"Conversation {conversation_id} not found in session")
        
        conversation = session.conversations[conversation_id]
        message = conversation.add_message(role, content, metadata)
        
        # Persist message to database
        _repository.save_message(message, conversation_id)
        
        # Update conversation in database
        _repository.save_conversation(conversation)
        
        # Persist to Redis cache
        ConversationManager._persist_session(session)
        
        logger.info(f"Added {role.value} message to conversation {conversation_id}")
        return message
    
    @staticmethod
    def get_conversation(session_id: str, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve a specific conversation"""
        session = ConversationManager.get_session(session_id)
        if not session or conversation_id not in session.conversations:
            return None
        return session.conversations[conversation_id]
    
    @staticmethod
    def get_conversation_history(
        session_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Get conversation history"""
        conversation = ConversationManager.get_conversation(session_id, conversation_id)
        if not conversation:
            return []
        
        # Return most recent messages
        return conversation.messages[-limit:]
    
    @staticmethod
    def update_conversation_context(
        session_id: str,
        conversation_id: str,
        outlook: str,
        confidence: float,
        action: str
    ) -> None:
        """Update conversation context with latest analysis results"""
        conversation = ConversationManager.get_conversation(session_id, conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation.previous_outlook = outlook
        conversation.previous_confidence = confidence
        conversation.previous_action = action
        conversation.last_updated = datetime.now()
        
        # Persist to database
        _repository.update_conversation_context(
            conversation_id, outlook, confidence, action
        )
        
        # Persist to Redis cache
        session = ConversationManager.get_session(session_id)
        ConversationManager._persist_session(session)
        
        logger.info(f"Updated context for conversation {conversation_id}")
    
    @staticmethod
    def get_context_injection(session_id: str, conversation_id: str) -> str:
        """Get context string to inject into agent prompts"""
        conversation = ConversationManager.get_conversation(session_id, conversation_id)
        if not conversation or not conversation.messages:
            return ""
        
        return conversation.get_context_summary()
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete a session and its conversations"""
        if session_id in _sessions:
            del _sessions[session_id]
        
        # Delete from Redis
        try:
            if redis_client:
                redis_client.delete(f"session:{session_id}")
        except Exception as e:
            logger.warning(f"Failed to delete session from Redis: {e}")
        
        logger.info(f"Deleted session {session_id}")
        return True
    
    @staticmethod
    def cleanup_expired_sessions(max_age_days: int = 7) -> int:
        """Remove sessions older than max_age_days"""
        expired_count = 0
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        expired_ids = [
            sid for sid, session in _sessions.items()
            if session.last_accessed < cutoff
        ]
        
        for session_id in expired_ids:
            ConversationManager.delete_session(session_id)
            expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        return expired_count
    
    # Private persistence methods
    @staticmethod
    def _persist_session(session: ConversationSession) -> None:
        """Persist session to Redis"""
        try:
            if not redis_client:
                return
            
            # Check if redis_client has setex method (real Redis)
            if not hasattr(redis_client, 'setex'):
                # Using InMemoryCache, skip persistence
                logger.debug("Using in-memory cache, skipping Redis persistence")
                return
            
            session_key = f"session:{session.session_id}"
            session_data = json.dumps(session.to_dict(), default=str)
            redis_client.setex(
                session_key,
                SESSION_EXPIRY,
                session_data
            )
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
    
    @staticmethod
    def _load_session(session_id: str) -> Optional[ConversationSession]:
        """Load session from Redis"""
        try:
            if not redis_client:
                return None
            
            session_key = f"session:{session_id}"
            session_data = redis_client.get(session_key)
            
            if not session_data:
                return None
            
            # Reconstruct session from JSON
            data = json.loads(session_data)
            session = ConversationSession(
                session_id=data["session_id"],
                user_id=data["user_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_accessed=datetime.fromisoformat(data["last_accessed"])
            )
            
            # Reconstruct conversations
            for conv_id, conv_data in data.get("conversations", {}).items():
                messages = [
                    ConversationMessage(
                        id=msg["id"],
                        role=MessageRole(msg["role"]),
                        content=msg["content"],
                        timestamp=datetime.fromisoformat(msg["timestamp"]),
                        metadata=msg.get("metadata", {})
                    )
                    for msg in conv_data.get("messages", [])
                ]
                
                context = ConversationContext(
                    conversation_id=conv_data["conversation_id"],
                    user_id=conv_data["user_id"],
                    asset_symbol=conv_data["asset_symbol"],
                    messages=messages,
                    created_at=datetime.fromisoformat(conv_data["created_at"]),
                    last_updated=datetime.fromisoformat(conv_data["last_updated"]),
                    previous_outlook=conv_data.get("previous_outlook"),
                    previous_confidence=conv_data.get("previous_confidence"),
                    previous_action=conv_data.get("previous_action"),
                    metadata=conv_data.get("metadata", {})
                )
                session.conversations[conv_id] = context
            
            return session
        
        except Exception as e:
            logger.error(f"Failed to load session from Redis: {e}")
            return None
    
    @staticmethod
    def get_all_sessions_for_user(user_id: str) -> List[ConversationSession]:
        """Get all sessions for a user"""
        return [s for s in _sessions.values() if s.user_id == user_id]
    
    @staticmethod
    def get_session_stats(session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session"""
        session = ConversationManager.get_session(session_id)
        if not session:
            return None
        
        total_messages = sum(len(c.messages) for c in session.conversations.values())
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "total_conversations": len(session.conversations),
            "total_messages": total_messages,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "age_minutes": (datetime.now() - session.created_at).total_seconds() / 60,
            "conversations": [
                {
                    "conversation_id": cid,
                    "asset_symbol": c.asset_symbol,
                    "message_count": len(c.messages),
                    "last_outlook": c.previous_outlook,
                    "last_confidence": c.previous_confidence
                }
                for cid, c in session.conversations.items()
            ]
        }
