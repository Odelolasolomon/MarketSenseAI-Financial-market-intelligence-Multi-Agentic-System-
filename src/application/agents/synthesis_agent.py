""""
Synthesis Agent - Coordinates all agents and synthesizes analysis
FIXED VERSION - Handles both dict and object returns from agents
LANGCHAIN VERSION - Integrates LangChain ConversationBufferMemory
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from src.application.agents.base_agent import BaseAgent
from src.application.agents.macro_analyst import MacroAnalyst
from src.application.agents.technical_analyst import TechnicalAnalyst
from src.application.agents.sentiment_analyst import SentimentAnalyst
from src.application.services.rag_service import RAGService
from src.application.services.tts_service import TTSService
from src.application.services.speech_service import SpeechService
from src.application.services.translation_service import TranslationService
from src.application.services.conversation_manager import ConversationManager
from src.application.services.langchain_memory_service import LangChainMemoryService
from src.domain.entities.analysis import Analysis, AgentAnalysis
from src.domain.entities.conversation import MessageRole
from src.domain.value_objects.timeframe import TimeframeVO
from src.config.constants import MarketOutlook, TradingAction, RiskLevel
from src.utilities.logger import get_logger

logger = get_logger(__name__)


class SynthesisAgent(BaseAgent):
    """Master agent that coordinates specialists and synthesizes results"""
    
    def __init__(self):
        super().__init__(
            name="Synthesis Agent",
            description="Coordinates specialist agents and synthesizes comprehensive investment analysis"
        )
        self.macro_analyst = MacroAnalyst()
        self.technical_analyst = TechnicalAnalyst()
        self.sentiment_analyst = SentimentAnalyst()
        self.rag_service = RAGService()
        self.tts_service = TTSService()
        self.speech_service = SpeechService()
        self.translation_service = TranslationService()
    
    def get_system_prompt(self) -> str:
        """Get system prompt for synthesis"""
        return """You are a senior investment analyst synthesizing multiple specialist analyses.

Your role is to:
1. Identify agreements and contradictions between analyses
2. Assess overall risk/reward profile
3. Provide clear investment thesis
4. Give specific actionable recommendations
5. Highlight key risks and uncertainties

Provide synthesis in JSON format:
{
    "executive_summary": "Clear bottom-line assessment",
    "investment_thesis": "Detailed reasoning",
    "outlook": "extremely_bearish/bearish/neutral/bullish/extremely_bullish",
    "trading_action": "strong_buy/buy/hold/sell/strong_sell/wait",
    "position_sizing": "small/medium/large",
    "entry_points": [price1, price2, ...],
    "stop_loss": price,
    "time_horizon": "short/medium/long",
    "bullish_factors": ["factor1", ...],
    "bearish_factors": ["factor1", ...],
    "critical_factors": ["factor1", ...],
    "key_risks": ["risk1", ...],
    "risk_mitigations": ["mitigation1", ...],
    "confidence": 0.0-1.0
}"""
    
    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """
        Safely get value from either dict or object with attribute
        
        Args:
            obj: Dictionary or object
            key: Key/attribute name
            default: Default value if not found
            
        Returns:
            Value or default
        """
        if obj is None:
            return default
        
        # If it's a dict, use .get()
        if isinstance(obj, dict):
            return obj.get(key, default)
        
        # If it's an object, use getattr()
        if hasattr(obj, key):
            return getattr(obj, key, default)
        
        # If it has to_dict method, convert and try again
        if hasattr(obj, 'to_dict'):
            try:
                dict_version = obj.to_dict()
                return dict_version.get(key, default)
            except Exception:
                pass
        
        return default
    
    def _ensure_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Ensure object is converted to dictionary
        
        Args:
            obj: Object or dict to convert
            
        Returns:
            Dictionary representation
        """
        if isinstance(obj, dict):
            return obj
        
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            try:
                return obj.to_dict()
            except Exception as e:
                logger.warning(f"Failed to convert object to dict: {e}")
        
        # If it's an object with attributes, create dict from attributes
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        
        # Last resort: return empty dict
        logger.warning(f"Could not convert object of type {type(obj)} to dict")
        return {}
    
    async def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Analysis:
        """
        Coordinate all agents and synthesize comprehensive analysis
        
        Args:
            query: Investment query
            context: Additional context including asset and timeframe
            
        Returns:
            Complete Analysis entity
        """
        try:
            logger.info(f"Synthesis Agent coordinating analysis: {query}")
            
            # Translate query to English if needed
            user_language = context.get("language", "en") if context else "en"
            query_in_english = self.translation_service.translate_text(query, src=user_language, dest="en")
            
            asset_symbol = context.get("asset_symbol", "MARKET") if context else "MARKET"
            
            # Handle LangChain conversation memory
            memory_id = context.get("memory_id") if context else None
            if not memory_id:
                # Create new memory if not provided
                memory_id, _ = LangChainMemoryService.create_memory()
                logger.info(f"Created new LangChain memory: {memory_id}")
            
            # Get or load existing memory
            langchain_memory = LangChainMemoryService.get_memory(memory_id)
            if not langchain_memory:
                memory_id, langchain_memory = LangChainMemoryService.create_memory(memory_id)
            
            # Get formatted conversation history
            memory_variables = LangChainMemoryService.get_memory_variables(memory_id)
            conversation_history = memory_variables.get("history", "")
            
            # Append conversation history to query if available
            enriched_query = f"{query_in_english}\n\n[Conversation History:\n{conversation_history}]" if conversation_history else query_in_english
            
            if conversation_history:
                logger.info(f"Injecting LangChain conversation history ({LangChainMemoryService.get_message_count(memory_id)} messages)")
            
            # Store memory_id in context for later use
            if context:
                context["memory_id"] = memory_id
            
            # Retrieve context using RAGService
            documents = await self.rag_service.query_collection(query_in_english, "macro")
            logger.info(f"Retrieved {len(documents)} documents for query: {query_in_english}")
            
            # Execute all specialist agents in parallel
            macro_task = self.macro_analyst.analyze(enriched_query, context)
            technical_task = self.technical_analyst.analyze(enriched_query, context)
            sentiment_task = self.sentiment_analyst.analyze(enriched_query, context)
            
            macro_result, technical_result, sentiment_result = await asyncio.gather(
                macro_task, technical_task, sentiment_task,
                return_exceptions=True
            )
            
            # Handle any errors
            if isinstance(macro_result, Exception):
                logger.error(f"Macro analyst error: {str(macro_result)}")
                macro_result = {"error": str(macro_result), "summary": "Error in macro analysis"}
            
            if isinstance(technical_result, Exception):
                logger.error(f"Technical analyst error: {str(technical_result)}")
                technical_result = {"error": str(technical_result), "summary": "Error in technical analysis"}
            
            if isinstance(sentiment_result, Exception):
                logger.error(f"Sentiment analyst error: {str(sentiment_result)}")
                sentiment_result = {"error": str(sentiment_result), "summary": "Error in sentiment analysis"}
            
            # Ensure all results are dicts (convert objects if needed)
            macro_result = self._ensure_dict(macro_result)
            technical_result = self._ensure_dict(technical_result)
            sentiment_result = self._ensure_dict(sentiment_result)
            
            logger.info(f"Agent results - Macro: {type(macro_result)}, Technical: {type(technical_result)}, Sentiment: {type(sentiment_result)}")
            
            # Convert SentimentAnalysis to dict immediately
            if hasattr(sentiment_result, 'to_dict') and not isinstance(sentiment_result, dict):
                sentiment_result = sentiment_result.to_dict()
            
            # Also convert macro and technical results to dicts if they have to_dict method
            if hasattr(macro_result, 'to_dict') and not isinstance(macro_result, dict):
                macro_result = macro_result.to_dict()
                
            if hasattr(technical_result, 'to_dict') and not isinstance(technical_result, dict):
                technical_result = technical_result.to_dict()
            
            # Synthesize results
            synthesis = await self._synthesize_results(
                query_in_english,
                asset_symbol,
                macro_result,
                technical_result,
                sentiment_result
            )
            
            # Translate response back to user's language
            translated_summary = self.translation_service.translate_text(
                synthesis.get("executive_summary", ""), src="en", dest=user_language
            )
            synthesis["executive_summary"] = translated_summary
            
            # Convert response to speech if requested
            if context.get("audio_output", False):
                audio_path = self.tts_service.text_to_speech(translated_summary, language=user_language)
                synthesis["audio_path"] = audio_path
            
            # Create Analysis entity
            analysis = self._create_analysis_entity(
                query=query,
                asset_symbol=asset_symbol,
                synthesis=synthesis,
                macro_result=macro_result,
                technical_result=technical_result,
                sentiment_result=sentiment_result
            )
            
            # Store in LangChain memory
            try:
                assistant_response = synthesis.get("final_response", synthesis.get("executive_summary", ""))
                
                # Add query and response to LangChain memory
                LangChainMemoryService.add_messages(
                    memory_id,
                    user_message=query,
                    ai_message=assistant_response
                )
                logger.info(f"Stored query/response in LangChain memory: {memory_id}")
                
            except Exception as e:
                logger.error(f"Error storing in LangChain memory: {str(e)}")
            
            # Also store in legacy conversation memory if available (backward compatibility)
            session_id = context.get("session_id") if context else None
            conversation_id = context.get("conversation_id") if context else None
            
            if session_id and conversation_id:
                try:
                    # Add user query to conversation
                    ConversationManager.add_message(
                        session_id,
                        conversation_id,
                        MessageRole.USER,
                        query,
                        metadata={"asset_symbol": asset_symbol}
                    )
                    
                    # Add assistant response to conversation
                    assistant_response = synthesis.get("final_response", synthesis.get("executive_summary", ""))
                    ConversationManager.add_message(
                        session_id,
                        conversation_id,
                        MessageRole.ASSISTANT,
                        assistant_response,
                        metadata={
                            "outlook": synthesis.get("outlook"),
                            "confidence": synthesis.get("confidence"),
                            "action": synthesis.get("trading_action")
                        }
                    )
                    
                    # Update conversation context with latest analysis
                    ConversationManager.update_conversation_context(
                        session_id,
                        conversation_id,
                        outlook=synthesis.get("outlook", "neutral"),
                        confidence=float(synthesis.get("confidence", 0.5)),
                        action=synthesis.get("trading_action", "hold")
                    )
                    
                    logger.info(f"Stored analysis in conversation memory for {conversation_id}")
                except Exception as e:
                    logger.warning(f"Failed to store in conversation memory: {e}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in Synthesis Agent: {str(e)}", exc_info=True)
            raise
    
    async def _synthesize_results(
        self,
        query: str,
        asset_symbol: str,
        macro: Dict,
        technical: Dict,
        sentiment: Dict
    ) -> Dict[str, Any]:
        """Create a deterministic, section-by-section synthesis"""
        
        def _classify_text_to_direction(text: str) -> str:
            if not text:
                return "neutral"
            t = text.lower()
            if any(k in t for k in ["bull", "positive", "up", "higher", "rally"]):
                return "bullish"
            if any(k in t for k in ["bear", "negative", "down", "lower", "sell"]):
                return "bearish"
            return "neutral"
        
        # Extract summaries and confidences using safe_get
        macro_summary = self._safe_get(macro, "summary", "")
        technical_summary = self._safe_get(technical, "summary", "")
        sentiment_summary = self._safe_get(sentiment, "summary", "")
        
        macro_conf = float(self._safe_get(macro, "confidence", 0.5) or 0.5)
        technical_conf = float(self._safe_get(technical, "confidence", 0.5) or 0.5)
        sentiment_conf = float(self._safe_get(sentiment, "confidence", 0.5) or 0.5)
        
        # Classify outlooks/trends
        macro_dir = _classify_text_to_direction(self._safe_get(macro, "outlook", macro_summary))
        technical_dir = _classify_text_to_direction(self._safe_get(technical, "trend", technical_summary))
        sentiment_dir = _classify_text_to_direction(self._safe_get(sentiment, "sentiment_label", sentiment_summary))
        
        directions = [macro_dir, technical_dir, sentiment_dir]
        
        # Majority vote for final outlook
        bullish_count = sum(1 for d in directions if d == "bullish")
        bearish_count = sum(1 for d in directions if d == "bearish")
        
        if bullish_count > bearish_count:
            final_outlook = "bullish"
        elif bearish_count > bullish_count:
            final_outlook = "bearish"
        else:
            final_outlook = "neutral"
        
        # Determine trading action
        if final_outlook == "bullish":
            trading_action = "buy"
        elif final_outlook == "bearish":
            trading_action = "sell"
        else:
            trading_action = "hold"
        
        # Position sizing based on confidence
        avg_conf = (macro_conf + technical_conf + sentiment_conf) / 3.0
        if avg_conf >= 0.75:
            position_sizing = "large"
        elif avg_conf >= 0.6:
            position_sizing = "medium"
        else:
            position_sizing = "small"
        
        # Collect factors and risks
        def _collect_list(field: str, *sources: Dict) -> List[str]:
            items = []
            for s in sources:
                field_value = self._safe_get(s, field, [])
                if field_value:
                    for it in field_value:
                        if isinstance(it, str) and it.strip() and it not in items:
                            items.append(it)
            return items
        
        bullish_factors = _collect_list("bullish_factors", macro, technical, sentiment)
        bearish_factors = _collect_list("bearish_factors", macro, technical, sentiment)
        critical_factors = _collect_list("critical_factors", macro, technical, sentiment)
        key_risks = _collect_list("key_risks", macro, technical, sentiment)
        risk_mitigations = _collect_list("risk_mitigations", macro, technical, sentiment)
        
        # Build investment thesis
        thesis_parts = []
        for src in (macro, technical, sentiment):
            t = self._safe_get(src, "investment_thesis") or self._safe_get(src, "detailed_analysis")
            if isinstance(t, str) and t.strip():
                thesis_parts.append(t.strip())
        
        investment_thesis = " \n\n ".join(thesis_parts) if thesis_parts else "Combined analysis from specialists."
        
        def _short(text: str, max_words: int = 40) -> str:
            if not text:
                return ""
            parts = text.split(".")
            first = parts[0].strip()
            words = first.split()
            if len(words) <= max_words:
                return first if first.endswith('.') else first + '.'
            return ' '.join(words[:max_words]) + '...'
        
        mac_short = _short(macro_summary, 40)
        tech_short = _short(technical_summary, 40)
        sent_short = _short(sentiment_summary, 40)
        
        executive_summary = (
            f"Technical analysis summary: {tech_short}\n"
            f"Macro analyst summary: {mac_short}\n"
            f"Sentiment analyst summary: {sent_short}\n"
            f"Final: Outlook={final_outlook}. Recommendation={trading_action} (position={position_sizing}; confidence={round(avg_conf,2)})."
        )
        
        synthesis = {
            "sections": {
                "macro": macro,
                "technical": technical,
                "sentiment": sentiment
            },
            "executive_summary": executive_summary,
            "investment_thesis": investment_thesis,
            "outlook": final_outlook,
            "trading_action": trading_action,
            "position_sizing": position_sizing,
            "entry_points": [],
            "stop_loss": None,
            "time_horizon": "medium",
            "bullish_factors": bullish_factors,
            "bearish_factors": bearish_factors,
            "critical_factors": critical_factors,
            "key_risks": key_risks,
            "risk_mitigations": risk_mitigations,
            "confidence": round(avg_conf, 4),
            "technical_analysis_summary": tech_short,
            "macro_analysis_summary": mac_short,
            "sentiment_analysis_summary": sent_short,
            "final_response": f"Outlook: {final_outlook}. Action: {trading_action}. Position: {position_sizing}. Confidence: {round(avg_conf,2)}."
        }
        
        return synthesis
    
    def _create_analysis_entity(
        self,
        query: str,
        asset_symbol: str,
        synthesis: Dict[str, Any],
        macro_result: Dict[str, Any],
        technical_result: Dict[str, Any],
        sentiment_result: Dict[str, Any]
    ) -> Analysis:
        """Create Analysis entity from results using safe_get"""
        
        # Create AgentAnalysis objects using _safe_get
        macro_analysis = AgentAnalysis(
            agent_name=self._safe_get(macro_result, "agent_name", "Macro Analyst"),
            summary=self._safe_get(macro_result, "summary", ""),
            confidence=self._safe_get(macro_result, "confidence", 0.5),
            key_factors=self._safe_get(macro_result, "key_factors", []),
            data_sources=self._safe_get(macro_result, "data_sources", []),
            detailed_analysis=self._safe_get(macro_result, "detailed_analysis", {})
        )
        
        technical_analysis = AgentAnalysis(
            agent_name=self._safe_get(technical_result, "agent_name", "Technical Analyst"),
            summary=self._safe_get(technical_result, "summary", ""),
            confidence=self._safe_get(technical_result, "confidence", 0.5),
            key_factors=self._safe_get(technical_result, "key_factors", []),
            data_sources=self._safe_get(technical_result, "data_sources", []),
            detailed_analysis=self._safe_get(technical_result, "detailed_analysis", {})
        )
        
        sentiment_analysis = AgentAnalysis(
            agent_name=self._safe_get(sentiment_result, "agent_name", "Sentiment Analyst"),
            summary=self._safe_get(sentiment_result, "summary", ""),
            confidence=self._safe_get(sentiment_result, "confidence", 0.5),
            key_factors=self._safe_get(sentiment_result, "key_factors", []),
            data_sources=self._safe_get(sentiment_result, "data_sources", []),
            detailed_analysis=self._safe_get(sentiment_result, "detailed_analysis", {})
        )
        
        # Calculate overall confidence
        confidences = [
            self._safe_get(macro_result, "confidence", 0.5),
            self._safe_get(technical_result, "confidence", 0.5),
            self._safe_get(sentiment_result, "confidence", 0.5)
        ]
        overall_confidence = sum(confidences) / len(confidences)
        
        # Calculate risk score
        risk_score = 1 - overall_confidence
        
        return Analysis(
            query=query,
            asset_symbol=asset_symbol,
            executive_summary=synthesis.get("executive_summary", ""),
            investment_thesis=synthesis.get("investment_thesis", ""),
            outlook=MarketOutlook(synthesis.get("outlook", "neutral")),
            overall_confidence=overall_confidence,
            risk_level=self._get_risk_level(risk_score),
            risk_score=risk_score,
            trading_action=TradingAction(synthesis.get("trading_action", "hold")),
            position_sizing=synthesis.get("position_sizing", "small"),
            entry_points=synthesis.get("entry_points", []),
            stop_loss=synthesis.get("stop_loss"),
            time_horizon=synthesis.get("time_horizon", "medium"),
            bullish_factors=synthesis.get("bullish_factors", []),
            bearish_factors=synthesis.get("bearish_factors", []),
            critical_factors=synthesis.get("critical_factors", []),
            key_risks=synthesis.get("key_risks", []),
            risk_mitigations=synthesis.get("risk_mitigations", []),
            macro_analysis=macro_analysis,
            technical_analysis=technical_analysis,
            sentiment_analysis=sentiment_analysis
        )
    
    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        if risk_score < 0.2:
            return RiskLevel.VERY_LOW
        elif risk_score < 0.4:
            return RiskLevel.LOW
        elif risk_score < 0.6:
            return RiskLevel.MEDIUM
        elif risk_score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH