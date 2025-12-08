"""
Conversation Routes - API endpoints for conversation memory management
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.application.services.conversation_manager import ConversationManager
from src.domain.entities.conversation import MessageRole
from src.utilities.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request to create a new session"""
    user_id: str = Field(..., description="Unique user identifier")


class CreateSessionResponse(BaseModel):
    """Response with new session"""
    session_id: str
    user_id: str
    created_at: datetime


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    asset_symbol: str = Field(..., description="Asset symbol (e.g., BTC, EUR/USD)")
    conversation_id: Optional[str] = Field(None, description="Optional custom conversation ID")


class CreateConversationResponse(BaseModel):
    """Response with new conversation"""
    session_id: str
    conversation_id: str
    asset_symbol: str
    created_at: datetime


class MessageRequest(BaseModel):
    """Request to add a message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class MessageResponse(BaseModel):
    """Response with stored message"""
    id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history"""
    conversation_id: str
    asset_symbol: str
    messages: List[MessageResponse]
    context_summary: str


class ConversationContextUpdate(BaseModel):
    """Request to update conversation context"""
    outlook: str = Field(..., description="Latest market outlook")
    confidence: float = Field(..., description="Confidence score 0-1")
    action: str = Field(..., description="Trading action")


class SessionStatsResponse(BaseModel):
    """Response with session statistics"""
    session_id: str
    user_id: str
    total_conversations: int
    total_messages: int
    created_at: datetime
    last_accessed: datetime
    age_minutes: float
    conversations: List[Dict[str, Any]]


# Routes
@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new user session for conversation tracking"""
    try:
        session = ConversationManager.create_session(request.user_id)
        return CreateSessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    session_id: str,
    request: CreateConversationRequest
) -> CreateConversationResponse:
    """Create a new conversation within a session"""
    try:
        conversation = ConversationManager.create_conversation(
            session_id,
            request.asset_symbol,
            request.conversation_id
        )
        return CreateConversationResponse(
            session_id=session_id,
            conversation_id=conversation.conversation_id,
            asset_symbol=conversation.asset_symbol,
            created_at=conversation.created_at
        )
    except ValueError as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/sessions/{session_id}/conversations/{conversation_id}/messages",
    response_model=MessageResponse
)
async def add_message(
    session_id: str,
    conversation_id: str,
    request: MessageRequest
) -> MessageResponse:
    """Add a message to a conversation"""
    try:
        # Validate role
        try:
            role = MessageRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be 'user' or 'assistant'"
            )
        
        message = ConversationManager.add_message(
            session_id,
            conversation_id,
            role,
            request.content,
            request.metadata
        )
        
        return MessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp,
            metadata=message.metadata
        )
    except ValueError as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/sessions/{session_id}/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse
)
async def get_conversation_history(
    session_id: str,
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max messages to return")
) -> ConversationHistoryResponse:
    """Retrieve conversation history"""
    try:
        conversation = ConversationManager.get_conversation(session_id, conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = ConversationManager.get_conversation_history(session_id, conversation_id, limit)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            asset_symbol=conversation.asset_symbol,
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role.value,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.metadata
                )
                for msg in messages
            ],
            context_summary=conversation.get_context_summary()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/sessions/{session_id}/conversations/{conversation_id}/context"
)
async def update_conversation_context(
    session_id: str,
    conversation_id: str,
    request: ConversationContextUpdate
):
    """Update conversation context with latest analysis"""
    try:
        ConversationManager.update_conversation_context(
            session_id,
            conversation_id,
            request.outlook,
            request.confidence,
            request.action
        )
        return {
            "status": "success",
            "message": "Conversation context updated"
        }
    except ValueError as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(session_id: str) -> SessionStatsResponse:
    """Get statistics for a session"""
    try:
        stats = ConversationManager.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionStatsResponse(
            session_id=stats["session_id"],
            user_id=stats["user_id"],
            total_conversations=stats["total_conversations"],
            total_messages=stats["total_messages"],
            created_at=datetime.fromisoformat(stats["created_at"]),
            last_accessed=datetime.fromisoformat(stats["last_accessed"]),
            age_minutes=stats["age_minutes"],
            conversations=stats["conversations"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its conversations"""
    try:
        ConversationManager.delete_session(session_id)
        return {
            "status": "success",
            "message": f"Session {session_id} deleted"
        }
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_sessions(max_age_days: int = Query(7, ge=1)):
    """Clean up expired sessions"""
    try:
        count = ConversationManager.cleanup_expired_sessions(max_age_days)
        return {
            "status": "success",
            "message": f"Cleaned up {count} expired sessions"
        }
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    session_id: str,
    request: CreateConversationRequest
) -> CreateConversationResponse:
    """Create a new conversation within a session"""
    try:
        conversation = ConversationManager.create_conversation(
            session_id,
            request.asset_symbol,
            request.conversation_id
        )
        return CreateConversationResponse(
            session_id=session_id,
            conversation_id=conversation.conversation_id,
            asset_symbol=conversation.asset_symbol,
            created_at=conversation.created_at
        )
    except ValueError as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/sessions/{session_id}/conversations/{conversation_id}/messages",
    response_model=MessageResponse
)
async def add_message(
    session_id: str,
    conversation_id: str,
    request: MessageRequest
) -> MessageResponse:
    """Add a message to a conversation"""
    try:
        # Validate role
        try:
            role = MessageRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be 'user' or 'assistant'"
            )
        
        message = ConversationManager.add_message(
            session_id,
            conversation_id,
            role,
            request.content,
            request.metadata
        )
        
        return MessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp,
            metadata=message.metadata
        )
    except ValueError as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/sessions/{session_id}/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse
)
async def get_conversation_history(
    session_id: str,
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max messages to return")
) -> ConversationHistoryResponse:
    """Retrieve conversation history"""
    try:
        conversation = ConversationManager.get_conversation(session_id, conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = ConversationManager.get_conversation_history(session_id, conversation_id, limit)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            asset_symbol=conversation.asset_symbol,
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role.value,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.metadata
                )
                for msg in messages
            ],
            context_summary=conversation.get_context_summary()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/sessions/{session_id}/conversations/{conversation_id}/context"
)
async def update_conversation_context(
    session_id: str,
    conversation_id: str,
    request: ConversationContextUpdate
):
    """Update conversation context with latest analysis"""
    try:
        ConversationManager.update_conversation_context(
            session_id,
            conversation_id,
            request.outlook,
            request.confidence,
            request.action
        )
        return {
            "status": "success",
            "message": "Conversation context updated"
        }
    except ValueError as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(session_id: str) -> SessionStatsResponse:
    """Get statistics for a session"""
    try:
        stats = ConversationManager.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionStatsResponse(
            session_id=stats["session_id"],
            user_id=stats["user_id"],
            total_conversations=stats["total_conversations"],
            total_messages=stats["total_messages"],
            created_at=datetime.fromisoformat(stats["created_at"]),
            last_accessed=datetime.fromisoformat(stats["last_accessed"]),
            age_minutes=stats["age_minutes"],
            conversations=stats["conversations"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its conversations"""
    try:
        ConversationManager.delete_session(session_id)
        return {
            "status": "success",
            "message": f"Session {session_id} deleted"
        }
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_sessions(max_age_days: int = Query(7, ge=1)):
    """Clean up expired sessions"""
    try:
        count = ConversationManager.cleanup_expired_sessions(max_age_days)
        return {
            "status": "success",
            "message": f"Cleaned up {count} expired sessions"
        }
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_conversations(user_id: str):
    """
    Get all conversations for a specific user from database
    
    Returns a flat list of conversation summaries sorted by date (newest first)
    """
    try:
        # Import repository
        from src.infrastructure.repositories.conversation_repository import ConversationRepository
        repository = ConversationRepository()
        
        # Query database for user conversations
        conversations = repository.get_user_conversations(user_id, limit=50)
        
        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
        return conversations
        
    except Exception as e:
        logger.error(f"Failed to get user conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
