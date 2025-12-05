"""
LangChain Memory REST API Routes
Provides endpoints for managing LangChain conversation memory
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from src.application.services.langchain_memory_service import LangChainMemoryService
from src.utilities.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/langchain-memory",
    tags=["LangChain Memory"]
)


@router.post("/create")
async def create_memory(
    memory_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Create a new LangChain ConversationBufferMemory instance
    
    Args:
        memory_id: Optional memory ID (generates if not provided)
        
    Returns:
        Memory ID and creation confirmation
    """
    try:
        created_id, memory = LangChainMemoryService.create_memory(memory_id=memory_id)
        return {
            "success": True,
            "memory_id": created_id,
            "message": "Memory instance created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/add-message")
async def add_message(
    memory_id: str,
    user_message: str,
    ai_message: str
) -> Dict[str, Any]:
    """
    Add user and AI messages to memory
    
    Args:
        memory_id: Memory instance ID
        user_message: User message content
        ai_message: AI message content
        
    Returns:
        Success status and message count
    """
    try:
        success = LangChainMemoryService.add_messages(
            memory_id,
            user_message=user_message,
            ai_message=ai_message
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        count = LangChainMemoryService.get_message_count(memory_id)
        return {
            "success": True,
            "memory_id": memory_id,
            "message_count": count,
            "message": "Messages added successfully"
        }
    except Exception as e:
        logger.error(f"Error adding messages: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/add-user-message")
async def add_user_message(
    memory_id: str,
    message: str
) -> Dict[str, Any]:
    """
    Add a user message to memory
    
    Args:
        memory_id: Memory instance ID
        message: Message content
        
    Returns:
        Success status
    """
    try:
        success = LangChainMemoryService.add_user_message(memory_id, message)
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "User message added successfully"
        }
    except Exception as e:
        logger.error(f"Error adding user message: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/add-ai-message")
async def add_ai_message(
    memory_id: str,
    message: str
) -> Dict[str, Any]:
    """
    Add an AI message to memory
    
    Args:
        memory_id: Memory instance ID
        message: Message content
        
    Returns:
        Success status
    """
    try:
        success = LangChainMemoryService.add_ai_message(memory_id, message)
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "AI message added successfully"
        }
    except Exception as e:
        logger.error(f"Error adding AI message: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/get/{memory_id}")
async def get_memory_content(memory_id: str) -> Dict[str, Any]:
    """
    Get memory content and formatted history
    
    Args:
        memory_id: Memory instance ID
        
    Returns:
        Memory variables and formatted history
    """
    try:
        variables = LangChainMemoryService.get_memory_variables(memory_id)
        
        if not variables:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        message_count = LangChainMemoryService.get_message_count(memory_id)
        
        return {
            "memory_id": memory_id,
            "message_count": message_count,
            "history": variables.get("history", ""),
            "variables": variables
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{memory_id}")
async def get_formatted_history(memory_id: str) -> Dict[str, Any]:
    """
    Get formatted conversation history
    
    Args:
        memory_id: Memory instance ID
        
    Returns:
        Formatted conversation history
    """
    try:
        history = LangChainMemoryService.get_formatted_history(memory_id)
        
        if history is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        message_count = LangChainMemoryService.get_message_count(memory_id)
        
        return {
            "memory_id": memory_id,
            "message_count": message_count,
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/{memory_id}")
async def export_conversation(memory_id: str) -> Dict[str, Any]:
    """
    Export conversation as structured data
    
    Args:
        memory_id: Memory instance ID
        
    Returns:
        Structured conversation export
    """
    try:
        export = LangChainMemoryService.export_conversation(memory_id)
        
        if not export:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return export
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/clear/{memory_id}")
async def clear_memory(memory_id: str) -> Dict[str, Any]:
    """
    Clear all messages from memory
    
    Args:
        memory_id: Memory instance ID
        
    Returns:
        Success status
    """
    try:
        success = LangChainMemoryService.clear_memory(memory_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory cleared successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing memory: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete/{memory_id}")
async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """
    Delete a memory instance
    
    Args:
        memory_id: Memory instance ID
        
    Returns:
        Success status
    """
    try:
        success = LangChainMemoryService.delete_memory(memory_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
