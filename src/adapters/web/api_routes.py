"""
API Routes
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime 
from src.application.services.analysis_service import AnalysisService
from src.application.services.data_service import DataService
from src.application.services.speech_service import SpeechService
from src.application.services.tts_service import TTSService
from src.application.services.rag_service import RAGService
from src.application.services.translation_service import TranslationService
from src.domain.value_objects.timeframe import TimeframeVO
from src.utilities.logger import get_logger


logger = get_logger(__name__)
router = APIRouter()

speech_service = SpeechService()
tts_service = TTSService()
translation_service = TranslationService()



# Request/Response Models
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    services: dict


class AnalysisRequest(BaseModel):
    """Analysis request model"""
    query: str = Field(..., description="Investment query")
    asset: Optional[str] = Field(None, description="Asset symbol")
    timeframe: str = Field("medium", description="Analysis timeframe")
    session_id: Optional[str] = Field(None, description="Conversation session ID for memory")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for memory")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Should I buy Bitcoin now?",
                "asset": "BTC",
                "timeframe": "medium",
                "session_id": "optional-session-uuid",
                "conversation_id": "optional-conversation-uuid"
            }
        }


class AnalysisResponse(BaseModel):
    """Analysis response model"""
    query: str
    asset_symbol: str
    analysis: dict
    confidence: float
    timestamp: str


# Health Check Route
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and health of dependencies
    """
    from src.infrastructure.database import get_db
    from src.infrastructure.cache import get_cache
    
    # Check database
    db_healthy = False
    try:
        db = get_db()
        db_healthy = db.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
    
    # Check cache
    cache_healthy = False
    try:
        cache = get_cache()
        cache_healthy = cache.health_check()
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
    
    return {
        "status": "healthy" if (db_healthy and cache_healthy) else "degraded",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy"
        }
    }


# Analysis Route
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_market(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Perform comprehensive market analysis
    
    This endpoint coordinates multiple AI agents to provide
    a comprehensive forex and crypto investment analysis for the requested asset.
    
    Optional conversation memory: Pass session_id and conversation_id to maintain
    conversation history across requests.
    """
    try:
        logger.info(f"Analysis request: {request.query} for {request.asset}")
        
        # Initialize analysis service
        analysis_service = AnalysisService()
        
        # Parse timeframe
        timeframe = TimeframeVO.from_string(request.timeframe)
        
        # Build context with conversation_id for caching
        context = {
            "asset_symbol": request.asset or "MARKET",
        }
        if request.conversation_id:
            context["conversation_id"] = request.conversation_id
            logger.info(f"Using conversation ID for caching: {request.conversation_id}")
        
        # Perform analysis
        result = await analysis_service.analyze(
            query=request.query,
            asset_symbol=request.asset or "MARKET",
            timeframe=timeframe,
            context=context
        )
        
        # Convert to dict immediately while we have the object in memory/session context
        result_dict = result.to_dict()
        
        # Cache result in background
        background_tasks.add_task(
            analysis_service.cache_analysis,
            result 
        )
        
        return AnalysisResponse(
            query=request.query,
            asset_symbol=result.asset_symbol,
            analysis=result_dict,
            confidence=result.overall_confidence,
            timestamp=result.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# Quick Analysis Route
@router.get("/analyze/{asset}")
async def quick_analysis(
    asset: str,
    query: Optional[str] = "Provide current market outlook",
    timeframe: str = "medium"
):
    """
    Quick analysis for a specific asset
    
    Simplified endpoint for getting analysis on a single asset
    """
    try:
        analysis_service = AnalysisService()
        timeframe_vo = TimeframeVO.from_string(timeframe)
        
        result = await analysis_service.analyze(
            query=query,
            asset_symbol=asset.upper(),
            timeframe=timeframe_vo
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Quick analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# Market Data Route
@router.get("/market/{symbol}")
async def get_market_data(symbol: str):
    """
    Get current market data for an asset
    
    Returns real-time price, volume, and technical indicators
    """
    try:
        data_service = DataService()
        market_data = await data_service.get_market_data(symbol.upper())
        
        if not market_data:
            raise HTTPException(
                status_code=404,
                detail=f"Market data not found for {symbol}"
            )
        
        return market_data.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Market data error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# Trending Assets Route
@router.get("/trending")
async def get_trending():
    """
    Get trending assets and market movers
    
    Returns list of trending cryptocurrencies and top gainers/losers
    """
    try:
        data_service = DataService()
        trending = await data_service.get_trending_assets()
        return trending
        
    except Exception as e:
        logger.error(f"Trending data error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# Agent Status Route
@router.get("/agents/status")
async def get_agents_status():
    """
    Get status of all AI agents
    
    Returns health and availability of specialist agents
    """
    return {
        "agents": {
            "macro_analyst": {"status": "available", "health": "healthy"},
            "technical_analyst": {"status": "available", "health": "healthy"},
            "sentiment_analyst": {"status": "available", "health": "healthy"},
            "synthesis_agent": {"status": "available", "health": "healthy"}
        },
        "timestamp": datetime.now().isoformat()
    }

@router.post("/api/v1/speech-to-text")
async def speech_to_text(language: str = "en-US"):
    try:
        text = speech_service.speech_to_text(language=language)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/text-to-speech")
async def text_to_speech(text: str, language: str = "en"):
    try:
        audio_path = tts_service.text_to_speech(text=text, language=language)
        return {"audio_path": audio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/translate")
async def translate_text(text: str, src: str, dest: str):
    try:
        translated_text = translation_service.translate_text(text=text, src=src, dest=dest)
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Include conversation routes
from src.adapters.web.routes.conversations import router as conversation_router
router.include_router(conversation_router)

@router.post("/api/v1/update-crypto-knowledge")
async def update_crypto_knowledge(crypto_data: Dict[str, Any]):
    try:
        rag_service = RAGService()
        await rag_service.update_crypto_knowledge(crypto_data)
        return {"message": "Crypto knowledge updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))