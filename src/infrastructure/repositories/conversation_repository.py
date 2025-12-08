"""
Conversation Repository - Database operations for conversations and messages
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.domain.entities.conversation import ConversationContext, ConversationMessage, MessageRole
from src.infrastructure.database import get_db
from src.utilities.logger import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    """Repository for conversation persistence"""
    
    def __init__(self):
        self.db = get_db()
    
    def save_conversation(self, conversation: ConversationContext) -> bool:
        """
        Save or update a conversation
        
        Args:
            conversation: ConversationContext to save
            
        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                # Check if conversation exists
                existing = session.query(ConversationContext).filter_by(
                    conversation_id=conversation.conversation_id
                ).first()
                
                if existing:
                    # Update existing
                    existing.last_updated = conversation.last_updated
                    existing.asset_symbol = conversation.asset_symbol
                    existing.previous_outlook = conversation.previous_outlook
                    existing.previous_confidence = conversation.previous_confidence
                    existing.previous_action = conversation.previous_action
                    existing.metadata = conversation.metadata
                    logger.info(f"Updated conversation: {conversation.conversation_id}")
                else:
                    # Insert new
                    session.add(conversation)
                    logger.info(f"Created conversation: {conversation.conversation_id}")
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            return False
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """
        Get a conversation by ID
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationContext or None
        """
        try:
            with self.db.get_session() as session:
                conversation = session.query(ConversationContext).filter_by(
                    conversation_id=conversation_id
                ).first()
                
                if conversation:
                    # Detach from session
                    session.expunge(conversation)
                    # Load messages separately
                    conversation.messages = self.get_messages(conversation_id)
                
                return conversation
                
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation summaries
        """
        try:
            with self.db.get_session() as session:
                conversations = session.query(ConversationContext).filter_by(
                    user_id=user_id
                ).order_by(
                    desc(ConversationContext.last_updated)
                ).limit(limit).all()
                
                # Convert to dictionaries with message counts
                result = []
                for conv in conversations:
                    message_count = session.query(ConversationMessage).filter_by(
                        conversation_id=conv.conversation_id
                    ).count()
                    
                    result.append({
                        "conversation_id": conv.conversation_id,
                        "session_id": conv.session_id,
                        "asset_symbol": conv.asset_symbol,
                        "message_count": message_count,
                        "model_outlook": conv.previous_outlook,
                        "created_at": conv.created_at.isoformat(),
                        "last_updated": conv.last_updated.isoformat(),
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            return []
    
    def save_message(self, message: ConversationMessage, conversation_id: str) -> bool:
        """
        Save a message to a conversation
        
        Args:
            message: ConversationMessage to save
            conversation_id: Conversation ID this message belongs to
            
        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                # Create a new message instance for the session
                # (avoid detached instance issues)
                new_message = ConversationMessage(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp,
                    metadata=message.metadata or {}
                )
                
                # Add conversation_id to metadata for foreign key simulation
                # (since we don't have a direct FK in the dataclass)
                if not hasattr(new_message, '_conversation_id'):
                    # Store it in metadata for now
                    new_message.metadata['conversation_id'] = conversation_id
                
                session.add(new_message)
                
                # Update conversation's last_updated and message_count
                conversation = session.query(ConversationContext).filter_by(
                    conversation_id=conversation_id
                ).first()
                
                if conversation:
                    conversation.last_updated = datetime.now()
                    # Message count will be calculated on query
                
                session.commit()
                logger.info(f"Saved message {message.id} to conversation {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return False
    
    def get_messages(
        self, 
        conversation_id: str, 
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Get messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages
            
        Returns:
            List of ConversationMessage objects
        """
        try:
            with self.db.get_session() as session:
                query = session.query(ConversationMessage).filter(
                    ConversationMessage.metadata['conversation_id'].astext == conversation_id
                ).order_by(ConversationMessage.timestamp)
                
                if limit:
                    query = query.limit(limit)
                
                messages = query.all()
                
                # Detach from session
                for msg in messages:
                    session.expunge(msg)
                
                return messages
                
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return []
    
    def update_conversation_context(
        self,
        conversation_id: str,
        outlook: Optional[str] = None,
        confidence: Optional[float] = None,
        action: Optional[str] = None
    ) -> bool:
        """
        Update conversation context from analysis results
        
        Args:
            conversation_id: Conversation ID
            outlook: Market outlook
            confidence: Confidence score
            action: Trading action
            
        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                conversation = session.query(ConversationContext).filter_by(
                    conversation_id=conversation_id
                ).first()
                
                if conversation:
                    if outlook:
                        conversation.previous_outlook = outlook
                    if confidence is not None:
                        conversation.previous_confidence = confidence
                    if action:
                        conversation.previous_action = action
                    
                    conversation.last_updated = datetime.now()
                    session.commit()
                    logger.info(f"Updated context for conversation {conversation_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            return False
