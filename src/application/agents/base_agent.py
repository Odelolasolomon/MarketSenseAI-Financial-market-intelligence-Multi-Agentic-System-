"""
Base Agent Class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.config.settings import get_settings
from src.utilities.logger import get_logger
from src.error_trace.exceptions import AgentExecutionError

logger = get_logger(__name__)
settings = get_settings()


class BaseAgent(ABC):
    """Abstract base class for all AI agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

        # Initialize Groq API client (active)
        self.groq_api_key = settings.groq_api_key
        logger.info(f"Groq API key loaded for {self.name}")

        # Initialize OpenAI client only if the API key is provided (inactive by default)
        self.client = None
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info(f"OpenAI client initialized for {self.name}")
            except ImportError:
                logger.warning("OpenAI library not installed. OpenAI client not initialized.")

        # Model and temperature settings
        self.model = settings.llm_model
        self.temperature = settings.agent_temperature
        logger.info(f"Initialized {self.name}")

    @abstractmethod
    async def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main analysis method - must be implemented by subclasses
        
        Args:
            query: Analysis query
            context: Additional context data
            
        Returns:
            Analysis results dictionary
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    async def execute_llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Execute LLM call with error handling
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            temperature: Optional temperature override
            
        Returns:
            LLM response text
        """
        if not self.client:
            raise AgentExecutionError(
                message="OpenAI client is not initialized. Cannot execute LLM call.",
                details={"agent": self.name}
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.temperature,
                max_tokens=2000
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM execution error in {self.name}: {str(e)}")
            raise AgentExecutionError(
                message=f"Failed to execute LLM call: {str(e)}",
                details={"agent": self.name}
            )

    def format_output(
        self,
        analysis: Dict[str, Any],
        confidence: float,
        key_factors: list
    ) -> Dict[str, Any]:
        """
        Format agent output in standard structure
        
        Args:
            analysis: Raw analysis data
            confidence: Confidence score (0-1)
            key_factors: List of key factors
            
        Returns:
            Formatted output dictionary
        """
        return {
            "agent_name": self.name,
            "summary": analysis.get("summary", ""),
            "confidence": min(max(confidence, 0.0), 1.0),
            "key_factors": key_factors,
            "detailed_analysis": analysis,
            "data_sources": analysis.get("data_sources", [])
        } 