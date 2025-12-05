"""
LangChain Conversation Memory Service
Integrates LangChain's ConversationBufferMemory with persistence layer
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from src.infrastructure.cache import get_cache
from src.utilities.logger import get_logger

logger = get_logger(__name__)

# In-memory storage of active memory instances
_memory_instances: Dict[str, ConversationBufferMemory] = {}
MEMORY_CACHE_PREFIX = "langchain_memory:"
MEMORY_EXPIRY = 7 * 24 * 60 * 60  # 7 days


class LangChainMemoryService:
    """
    Service for managing LangChain ConversationBufferMemory with persistence
    
    Combines LangChain's memory management with Redis persistence
    """
    
    # Class-level cache instance
    _cache = None
    
    @classmethod
    def get_cache(cls):
        """Get or initialize cache instance"""
        if cls._cache is None:
            cls._cache = get_cache()
        return cls._cache
    
    @staticmethod
    def create_memory(
        memory_id: Optional[str] = None,
        llm=None,
        return_messages: bool = True
    ) -> tuple[str, ConversationBufferMemory]:
        """
        Create a new ConversationBufferMemory instance
        
        Args:
            memory_id: Optional memory identifier (generates if not provided)
            llm: LLM instance (optional, for message serialization)
            return_messages: Whether to return messages as list
            
        Returns:
            Tuple of (memory_id, ConversationBufferMemory instance)
        """
        if memory_id is None:
            memory_id = str(uuid.uuid4())
        
        memory = ConversationBufferMemory(
            return_messages=return_messages,
            human_prefix="User",
            ai_prefix="Assistant"
        )
        
        _memory_instances[memory_id] = memory
        logger.info(f"Created ConversationBufferMemory: {memory_id}")
        
        return memory_id, memory
    
    @staticmethod
    def get_memory(memory_id: str) -> Optional[ConversationBufferMemory]:
        """Get memory instance by ID"""
        # Check in-memory first
        if memory_id in _memory_instances:
            return _memory_instances[memory_id]
        
        # Try to load from cache
        memory = LangChainMemoryService._load_from_cache(memory_id)
        if memory:
            _memory_instances[memory_id] = memory
            return memory
        
        return None
    
    @staticmethod
    def add_user_message(memory_id: str, message: str) -> bool:
        """
        Add a user message to memory
        
        Args:
            memory_id: Memory instance ID
            message: User message content
            
        Returns:
            True if successful
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False
        
        try:
            memory.chat_memory.add_user_message(message)
            LangChainMemoryService._persist_memory(memory_id, memory)
            logger.debug(f"Added user message to {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user message: {str(e)}")
            return False
    
    @staticmethod
    def add_ai_message(memory_id: str, message: str) -> bool:
        """
        Add an AI message to memory
        
        Args:
            memory_id: Memory instance ID
            message: AI message content
            
        Returns:
            True if successful
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False
        
        try:
            memory.chat_memory.add_ai_message(message)
            LangChainMemoryService._persist_memory(memory_id, memory)
            logger.debug(f"Added AI message to {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding AI message: {str(e)}")
            return False
    
    @staticmethod
    def add_messages(
        memory_id: str,
        user_message: str,
        ai_message: str
    ) -> bool:
        """
        Add both user and AI messages to memory
        
        Args:
            memory_id: Memory instance ID
            user_message: User message content
            ai_message: AI message content
            
        Returns:
            True if successful
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False
        
        try:
            memory.chat_memory.add_user_message(user_message)
            memory.chat_memory.add_ai_message(ai_message)
            LangChainMemoryService._persist_memory(memory_id, memory)
            logger.debug(f"Added conversation pair to {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding messages: {str(e)}")
            return False
    
    @staticmethod
    def get_memory_variables(memory_id: str) -> Dict[str, Any]:
        """
        Get formatted memory content for context injection
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            Dictionary with memory variables
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            return {}
        
        try:
            variables = memory.load_memory_variables({})
            logger.debug(f"Retrieved memory variables for {memory_id}")
            return variables
        except Exception as e:
            logger.error(f"Error loading memory variables: {str(e)}")
            return {}
    
    @staticmethod
    def get_formatted_history(memory_id: str) -> str:
        """
        Get formatted conversation history as string
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            Formatted conversation history
        """
        variables = LangChainMemoryService.get_memory_variables(memory_id)
        return variables.get("history", "")
    
    @staticmethod
    def get_message_count(memory_id: str) -> int:
        """
        Get number of messages in memory
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            Number of messages
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            return 0
        
        try:
            return len(memory.chat_memory.messages)
        except Exception as e:
            logger.error(f"Error getting message count: {str(e)}")
            return 0
    
    @staticmethod
    def clear_memory(memory_id: str) -> bool:
        """
        Clear all messages from memory
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            True if successful
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False
        
        try:
            memory.clear()
            LangChainMemoryService._persist_memory(memory_id, memory)
            logger.info(f"Cleared memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing memory: {str(e)}")
            return False
    
    @staticmethod
    def delete_memory(memory_id: str) -> bool:
        """
        Delete a memory instance
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            True if successful
        """
        try:
            if memory_id in _memory_instances:
                del _memory_instances[memory_id]
            
            # Delete from cache
            cache_key = f"{MEMORY_CACHE_PREFIX}{memory_id}"
            LangChainMemoryService.get_cache().delete(cache_key)
            
            logger.info(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            return False
    
    @staticmethod
    def _persist_memory(memory_id: str, memory: ConversationBufferMemory) -> None:
        """
        Persist memory to cache
        
        Args:
            memory_id: Memory instance ID
            memory: ConversationBufferMemory instance
        """
        try:
            cache_key = f"{MEMORY_CACHE_PREFIX}{memory_id}"
            
            # Serialize messages
            messages_data = []
            for msg in memory.chat_memory.messages:
                messages_data.append({
                    "type": msg.__class__.__name__,
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, "additional_kwargs", {})
                })
            
            # Store metadata
            metadata = {
                "memory_id": memory_id,
                "messages": messages_data,
                "created_at": datetime.utcnow().isoformat(),
                "message_count": len(messages_data)
            }
            
            LangChainMemoryService.get_cache().set(
                cache_key,
                metadata,
                ttl=MEMORY_EXPIRY
            )
            
            logger.debug(f"Persisted memory {memory_id} with {len(messages_data)} messages")
        except Exception as e:
            logger.error(f"Error persisting memory: {str(e)}")
    
    @staticmethod
    def _load_from_cache(memory_id: str) -> Optional[ConversationBufferMemory]:
        """
        Load memory from cache
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            ConversationBufferMemory instance or None
        """
        try:
            cache_key = f"{MEMORY_CACHE_PREFIX}{memory_id}"
            metadata = LangChainMemoryService.get_cache().get(cache_key)
            
            if not metadata:
                return None
            
            # Reconstruct memory
            memory = ConversationBufferMemory(
                return_messages=True,
                human_prefix="User",
                ai_prefix="Assistant"
            )
            
            # Restore messages
            messages_data = metadata.get("messages", [])
            for msg_data in messages_data:
                msg_type = msg_data.get("type")
                content = msg_data.get("content")
                
                if msg_type == "HumanMessage":
                    memory.chat_memory.add_user_message(content)
                elif msg_type == "AIMessage":
                    memory.chat_memory.add_ai_message(content)
            
            logger.debug(f"Loaded memory {memory_id} with {len(messages_data)} messages")
            return memory
        except Exception as e:
            logger.error(f"Error loading memory from cache: {str(e)}")
            return None
    
    @staticmethod
    def export_conversation(memory_id: str) -> Dict[str, Any]:
        """
        Export conversation as structured data
        
        Args:
            memory_id: Memory instance ID
            
        Returns:
            Dictionary with conversation data
        """
        memory = LangChainMemoryService.get_memory(memory_id)
        if not memory:
            return {}
        
        try:
            messages = []
            for msg in memory.chat_memory.messages:
                messages.append({
                    "role": "user" if msg.__class__.__name__ == "HumanMessage" else "assistant",
                    "content": msg.content,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return {
                "memory_id": memory_id,
                "message_count": len(messages),
                "messages": messages,
                "exported_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error exporting conversation: {str(e)}")
            return {}
