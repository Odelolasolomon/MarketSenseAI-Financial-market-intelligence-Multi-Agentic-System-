"""
Synthesis Agent - Coordinates all agents and synthesizes analysis
"""
import json
import asyncio
from typing import Dict, Any, Optional
from src.application.agents.base_agent import BaseAgent
from src.application.agents.macro_analyst import MacroAnalyst
from src.application.agents.technical_analyst import TechnicalAnalyst
from src.application.agents.sentiment_analyst import SentimentAnalyst
from src.domain.entities.analysis import Analysis, AgentAnalysis
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
            
            asset_symbol = context.get("asset_symbol", "MARKET") if context else "MARKET"
            
            # Execute all specialist agents in parallel
            macro_task = self.macro_analyst.analyze(query, context)
            technical_task = self.technical_analyst.analyze(query, context)
            sentiment_task = self.sentiment_analyst.analyze(query, context)
            
            macro_result, technical_result, sentiment_result = await asyncio.gather(
                macro_task, technical_task, sentiment_task,
                return_exceptions=True
            )
            
            # Handle any errors
            macro_result = macro_result if not isinstance(macro_result, Exception) else {"error": str(macro_result)}
            technical_result = technical_result if not isinstance(technical_result, Exception) else {"error": str(technical_result)}
            sentiment_result = sentiment_result if not isinstance(sentiment_result, Exception) else {"error": str(sentiment_result)}
            
            # Synthesize results
            synthesis = await self._synthesize_results(
                query,
                asset_symbol,
                macro_result,
                technical_result,
                sentiment_result
            )
            
            # Create AgentAnalysis objects
            macro_analysis = AgentAnalysis(
                agent_name=macro_result.get("agent_name", "Macro Analyst"),
                summary=macro_result.get("summary", ""),
                confidence=macro_result.get("confidence", 0.5),
                key_factors=macro_result.get("key_factors", []),
                data_sources=macro_result.get("data_sources", []),
                detailed_analysis=macro_result.get("detailed_analysis", {})
            )
            
            technical_analysis = AgentAnalysis(
                agent_name=technical_result.get("agent_name", "Technical Analyst"),
                summary=technical_result.get("summary", ""),
                confidence=technical_result.get("confidence", 0.5),
                key_factors=technical_result.get("key_factors", []),
                data_sources=technical_result.get("data_sources", []),
                detailed_analysis=technical_result.get("detailed_analysis", {})
            )
            
            sentiment_analysis = AgentAnalysis(
                agent_name=sentiment_result.get("agent_name", "Sentiment Analyst"),
                summary=sentiment_result.get("summary", ""),
                confidence=sentiment_result.get("confidence", 0.5),
                key_factors=sentiment_result.get("key_factors", []),
                data_sources=sentiment_result.get("data_sources", []),
                detailed_analysis=sentiment_result.get("detailed_analysis", {})
            )
            
            # Calculate overall confidence
            confidences = [
                macro_result.get("confidence", 0.5),
                technical_result.get("confidence", 0.5),
                sentiment_result.get("confidence", 0.5)
            ]
            overall_confidence = sum(confidences) / len(confidences)
            
            # Calculate risk score (simplified)
            risk_score = 1 - overall_confidence
            
            # Create Analysis entity
            analysis = Analysis(
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
        """Synthesize specialist results"""
        
        # Format analyses for prompt
        user_prompt = f"""Synthesize comprehensive investment analysis for: {query}
Asset: {asset_symbol}

MACRO ANALYSIS:
{json.dumps(macro, indent=2)}

TECHNICAL ANALYSIS:
{json.dumps(technical, indent=2)}

SENTIMENT ANALYSIS:
{json.dumps(sentiment, indent=2)}

Provide comprehensive synthesis with specific recommendations."""
        
        # Execute synthesis
        response = await self.execute_llm_call(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt
        )
        
        # Parse response
        try:
            synthesis = json.loads(response)
        except json.JSONDecodeError:
            synthesis = {
                "executive_summary": response,
                "outlook": "neutral",
                "confidence": 0.6
            }
        
        return synthesis
    
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