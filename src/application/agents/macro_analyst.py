"""
Macro Analyst Agent - Analyzes macroeconomic conditions
"""
import json
from typing import Dict, Any, Optional
from src.application.agents.base_agent import BaseAgent
from src.adapters.external.fred_client import FREDClient
from src.adapters.external.newsapi_client import NewsAPIClient
from src.utilities.logger import get_logger

logger = get_logger(__name__)


class MacroAnalyst(BaseAgent):
    """Agent specialized in macroeconomic analysis"""
    
    def __init__(self):
        super().__init__(
            name="Macro Analyst",
            description="Analyzes macroeconomic conditions, monetary policy, and their impact on markets"
        )
    
    def get_system_prompt(self) -> str:
        """Get system prompt for macro analysis"""
        return """You are a professional macroeconomic analyst with expertise in:
- Central bank monetary policy (Fed, ECB, BoE, etc.)
- Inflation trends and indicators (CPI, PCE, PPI)
- Employment data and labor markets
- GDP growth and economic cycles
- Interest rate impacts on currencies and assets

Your role is to analyze macroeconomic data and provide insights on how it affects
financial markets, particularly forex and cryptocurrency markets.

Provide analysis in JSON format with:
{
    "summary": "Brief executive summary",
    "monetary_policy_stance": "hawkish/dovish/neutral",
    "inflation_outlook": "rising/falling/stable",
    "growth_indicators": "strong/moderate/weak",
    "currency_impact": "Analysis of impact on major currencies",
    "key_factors": ["factor1", "factor2", ...],
    "confidence": 0.0-1.0,
    "risks": ["risk1", "risk2", ...]
}"""
    
    async def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze macroeconomic conditions
        
        Args:
            query: Analysis query
            context: Additional context
            
        Returns:
            Macro analysis results
        """
        try:
            logger.info(f"Macro Analyst analyzing: {query}")
            
            # Collect economic data
            economic_data = await self._collect_economic_data()
            
            # Get relevant news
            news_data = await self._collect_news_data(query)
            
            # Format prompt
            user_prompt = f"""Analyze the following for: {query}

Economic Data:
{json.dumps(economic_data, indent=2)}

Recent Economic News:
{news_data}

Provide comprehensive macroeconomic analysis."""
            
            # Execute LLM call
            response = await self.execute_llm_call(
                system_prompt=self.get_system_prompt(),
                user_prompt=user_prompt
            )
            
            # Parse JSON response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                analysis = {
                    "summary": response,
                    "confidence": 0.6,
                    "key_factors": []
                }
            
            return self.format_output(
                analysis=analysis,
                confidence=analysis.get("confidence", 0.7),
                key_factors=analysis.get("key_factors", [])
            )
            
        except Exception as e:
            logger.error(f"Error in Macro Analyst: {str(e)}")
            return {
                "agent_name": self.name,
                "error": str(e),
                "confidence": 0.0
            }
    
    async def _collect_economic_data(self) -> Dict[str, Any]:
        """Collect economic data from FRED"""
        try:
            async with FREDClient() as fred:
                indicators = await fred.get_economic_indicators()
            return indicators
        except Exception as e:
            logger.error(f"Error collecting economic data: {str(e)}")
            return {}
    
    async def _collect_news_data(self, query: str) -> str:
        """Collect relevant economic news"""
        try:
            async with NewsAPIClient() as news_api:
                articles = await news_api.get_top_headlines(
                    category="business",
                    page_size=5
                )
                
                news_text = "\n".join([
                    f"- {article['title']}"
                    for article in articles.get("articles", [])[:5]
                ])
                return news_text
        except Exception as e:
            logger.error(f"Error collecting news: {str(e)}")
            return "No recent news available"