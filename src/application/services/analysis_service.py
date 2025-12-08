"""
Analysis Service - Coordinates analysis workflow
"""
from typing import Optional, Dict
from datetime import datetime, timedelta
from src.application.agents.synthesis_agent import SynthesisAgent
from src.domain.entities.analysis import Analysis
from src.domain.value_objects.timeframe import TimeframeVO
from src.config.constants import MarketOutlook, TradingAction, RiskLevel
from src.infrastructure.cache import get_cache
from src.infrastructure.database import get_db
from src.config.constants import CACHE_ANALYSIS
from src.utilities.logger import get_logger
import json
import hashlib

logger = get_logger(__name__)


class AnalysisService:
    """Service for handling analysis requests"""
    
    # Simple in-memory cache for analysis (per conversation)
    _analysis_cache: Dict[str, Dict] = {}
    
    def __init__(self):
        self.synthesis_agent = SynthesisAgent()
        self.cache = get_cache()
        self.db = get_db()
    
    async def analyze(
        self,
        query: str,
        asset_symbol: str,
        timeframe: TimeframeVO,
        context: Optional[Dict] = None
    ) -> Analysis:
        """
        Perform comprehensive market analysis with smart caching
        
        Strategy:
        - First query about an asset: Run all agents, fetch fresh data
        - Follow-up questions: Use cached analysis from conversation
        - New asset: Run agents again
        - Stale data (>30 min): Refresh by running agents
        
        Conversation memory is handled by Gemini AI in the frontend.
        Backend only uses conversation_id to determine caching strategy.
        
        Args:
            query: Investment query
            asset_symbol: Asset symbol to analyze
            timeframe: Analysis timeframe
            context: Additional context including conversation_id for caching
            
        Returns:
            Complete analysis result
        """
        try:
            conversation_id = context.get("conversation_id") if context else None
            
            logger.info(f"Analyze request - Asset: {asset_symbol}, ConversationID: {conversation_id}")
            logger.info(f"Current cache keys: {list(self._analysis_cache.keys())}")
            
            # Step 1: Check if we have recent analysis for this asset in this conversation
            cached_analysis = None
            should_run_agents = True
            
            if conversation_id:
                cached_analysis = await self._get_cached_analysis_for_conversation(
                    conversation_id, asset_symbol
                )
                
                if cached_analysis:
                    logger.info(f"Found cached analysis for {asset_symbol} in conversation {conversation_id[:8]}...")
                    should_run_agents = False
                else:
                    logger.info(f"No cached analysis for {asset_symbol}, will run agents")
            else:
                logger.warning("No conversation_id provided, will run agents")
            
            # Step 2: Run agents or use cached data
            if should_run_agents:
                logger.info(f"Running agents for {asset_symbol} (new asset or stale data)")
                
                # Prepare base context
                analysis_context = {
                    "asset_symbol": asset_symbol,
                    "timeframe": timeframe.timeframe.value,
                    "days": timeframe.days,
                    "original_query": query
                }
                
                # Merge with passed context
                if context:
                    analysis_context.update(context)
                
                # Execute analysis with agents
                analysis = await self.synthesis_agent.analyze(query, analysis_context)
                
                # Store analysis for future use in this conversation
                if conversation_id:
                    await self._cache_analysis_for_conversation(
                        conversation_id, asset_symbol, analysis
                    )
                
            else:
                logger.info(f"Using cached analysis for {asset_symbol} (follow-up question)")
                
                # Use cached analysis to answer follow-up question
                # Gemini AI will handle the conversation context
                analysis = await self._create_analysis_from_cache(
                    query, asset_symbol, cached_analysis, timeframe
                )
            
            # Store in database
            await self._store_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis service error: {str(e)}")
            raise
    
    async def cache_analysis(self, analysis: Analysis):
        """Cache analysis result"""
        try:
            cache_key = self._generate_cache_key(
                analysis.query,
                analysis.asset_symbol,
                None,
                None
            )
            self.cache.set(
                cache_key,
                analysis.to_dict(),
                ttl=1800  # Cache for 30 minutes
            )
        except Exception as e:
            logger.error(f"Error caching analysis: {str(e)}")
    
    async def _store_analysis(self, analysis: Analysis):
        """Store analysis in the database"""
        try:
            # USE THE ASYNC VERSION
            async with self.db.get_session_async() as session:
                session.add(analysis)
                # Commit breaks the link, but we can refresh to get fresh data
                # However, with standard Session (not AsyncSession), commit is sync.
                # get_session_async is yielding a *synchronous* Session wrapper in an async manager.
                # So we use sync methods.
                session.commit()
                session.refresh(analysis)
                # Expunge checks the object out of the session so it persists after session.close()
                session.expunge(analysis)
                logger.info("Analysis stored successfully.")
        except Exception as e:
            logger.error(f"Error storing analysis: {str(e)}")
    
    def _generate_cache_key(
        self,
        query: str,
        asset_symbol: str,
        timeframe: Optional[TimeframeVO],
        context: Optional[Dict]
    ) -> str:
        """Generate cache key for analysis"""
        key_parts = [query, asset_symbol]
        
        if timeframe:
            key_parts.append(timeframe.timeframe.value)
        
        # Include relevant context parts in cache key
        if context:
            # Include conversation_id if present (for conversation memory)
            if 'conversation_id' in context:
                key_parts.append(f"conversation:{context['conversation_id']}")
            # Include asset_symbol from context if different
            if 'asset_symbol' in context and context['asset_symbol'] != asset_symbol:
                key_parts.append(f"ctx_asset:{context['asset_symbol']}")
        
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_analysis_id(self, analysis: Analysis) -> str:
        """Generate unique ID for analysis"""
        id_string = f"{analysis.query}:{analysis.asset_symbol}:{analysis.created_at}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
    
    async def get_cached_analysis(
        self,
        query: str,
        asset_symbol: str,
        timeframe: Optional[TimeframeVO] = None,
        context: Optional[Dict] = None
    ) -> Optional[Analysis]:
        """Retrieve cached analysis if available"""
        try:
            cache_key = self._generate_cache_key(query, asset_symbol, timeframe, context)
            cached = self.cache.get(cache_key)
            
            if cached:
                logger.info(f"Retrieved cached analysis for {asset_symbol}")
                if isinstance(cached, dict):
                    return Analysis.from_dict(cached)
                return cached
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached analysis: {str(e)}")
            return None
    
    async def clear_cache_for_context(
        self,
        conversation_id: str
    ):
        """Clear cached analyses for specific conversation"""
        try:
            logger.info(f"Clearing cache for conversation: {conversation_id}")
            # Clear from in-memory cache
            keys_to_delete = [k for k in self._analysis_cache.keys() if k.startswith(f"{conversation_id}:")]
            for key in keys_to_delete:
                del self._analysis_cache[key]
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    async def _get_cached_analysis_for_conversation(
        self,
        conversation_id: str,
        asset_symbol: str
    ) -> Optional[Dict]:
        """Get cached analysis for asset from conversation cache"""
        try:
            cache_key = f"{conversation_id}:{asset_symbol}"
            
            if cache_key not in self._analysis_cache:
                return None
            
            cached = self._analysis_cache[cache_key]
            
            # Check if data is still fresh (within 30 minutes)
            timestamp = cached.get("timestamp")
            if timestamp:
                analysis_time = datetime.fromisoformat(timestamp)
                age = datetime.now() - analysis_time
                
                if age > timedelta(minutes=30):
                    logger.info(f"Cached analysis for {asset_symbol} is stale ({age.seconds//60} min old)")
                    del self._analysis_cache[cache_key]
                    return None
            
            logger.info(f"Using fresh cached analysis for {asset_symbol}")
            return cached
            
        except Exception as e:
            logger.error(f"Error retrieving cached analysis: {e}")
            return None
    
    async def _cache_analysis_for_conversation(
        self,
        conversation_id: str,
        asset_symbol: str,
        analysis: Analysis
    ):
        """Store analysis in simple cache for future use"""
        try:
            cache_key = f"{conversation_id}:{asset_symbol}"
            
            # Store analysis data
            self._analysis_cache[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "outlook": analysis.outlook.value,
                "confidence": analysis.overall_confidence,
                "trading_action": analysis.trading_action.value,
                "technical_score": getattr(analysis.technical_analysis, 'confidence', 0.5) if analysis.technical_analysis else 0.5,
                "sentiment_score": getattr(analysis.sentiment_analysis, 'confidence', 0.5) if analysis.sentiment_analysis else 0.5,
                "fundamental_score": getattr(analysis.macro_analysis, 'confidence', 0.5) if analysis.macro_analysis else 0.5,
                "analysis_dict": analysis.to_dict()
            }
            
            logger.info(f"Cached analysis for {asset_symbol} in conversation {conversation_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Error caching analysis: {e}")
    
    async def _create_analysis_from_cache(
        self,
        query: str,
        asset_symbol: str,
        cached_analysis: Dict,
        timeframe: TimeframeVO
    ) -> Analysis:
        """Create analysis object from cached data"""
        try:
            # Reconstruct analysis from cached data
            analysis_dict = cached_analysis.get("analysis_dict", {})
            
            # Create a new analysis with the cached data but updated query
            analysis = Analysis(
                query=query,
                asset_symbol=asset_symbol,
                executive_summary=cached_analysis.get("outlook", "neutral"),
                investment_thesis="Based on previous analysis",
                outlook=MarketOutlook(cached_analysis.get("outlook", "neutral")),
                overall_confidence=cached_analysis.get("confidence", 0.5),
                risk_level=RiskLevel.MEDIUM,
                risk_score=0.5,
                trading_action=TradingAction(cached_analysis.get("trading_action", "hold")),
                position_sizing="medium",
                time_horizon="medium",
                created_at=datetime.now()
            )
            
            # Copy over detailed analysis if available
            # Skip enum fields and nested objects to avoid type mismatches
            skip_fields = [
                'query', 'created_at', 'updated_at',  # Datetime fields
                'outlook', 'trading_action', 'risk_level',  # Enums
                'macro_analysis', 'technical_analysis', 'sentiment_analysis'  # Nested objects
            ]
            if analysis_dict:
                for key, value in analysis_dict.items():
                    if hasattr(analysis, key) and key not in skip_fields:
                        try:
                            setattr(analysis, key, value)
                        except:
                            pass
            
            logger.info(f"Created analysis from cached data for follow-up question")
            return analysis
            
        except Exception as e:
            logger.error(f"Error creating analysis from cache: {e}")
            # Fallback: create basic analysis
            return Analysis(
                query=query,
                asset_symbol=asset_symbol,
                executive_summary="neutral",
                investment_thesis="Based on previous analysis",
                outlook=MarketOutlook.NEUTRAL,
                overall_confidence=0.5,
                risk_level=RiskLevel.MEDIUM,
                risk_score=0.5,
                trading_action=TradingAction.HOLD,
                position_sizing="medium",
                time_horizon="medium",
                created_at=datetime.now()
            )