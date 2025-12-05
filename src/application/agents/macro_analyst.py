"""
Crypto Macro Analyst Agent - Analyzes macroeconomic conditions for cryptocurrency markets
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from src.application.agents.base_agent import BaseAgent
from src.application.services.rag_service import RAGService
from src.application.services.translation_service import TranslationService
from src.adapters.external.fred_client import FREDClient
from src.utilities.logger import get_logger

# Import what's actually available
try:
    from src.adapters.external.newsapi_client import CryptoNewsScraper
    HAS_CRYPTO_NEWS_SCRAPER = True
except ImportError:
    HAS_CRYPTO_NEWS_SCRAPER = False

logger = get_logger(__name__)


class MacroAnalyst(BaseAgent):
    """Agent specialized in crypto-specific macroeconomic analysis"""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        # Call parent constructor with correct parameters
        super().__init__(
            name="Crypto Macro Analyst",
            description="Specializes in macroeconomic analysis for cryptocurrency markets including monetary policy, inflation, and regulatory impacts"
        )
        
        # Store model for use in LLM calls
        self.model = model
        
        # Initialize services
        self.rag_service = RAGService()
        self.translation_service = TranslationService()
        
        # Initialize FRED client for economic data
        self.fred_client = FREDClient()
        
        # Initialize crypto news scraper if available
        self.crypto_scraper = None
        if HAS_CRYPTO_NEWS_SCRAPER:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # Use CryptoNewsScraper for crypto-specific news
            self.crypto_scraper = CryptoNewsScraper(
                serper_api_key=settings.serper_api_key,
                serpapi_key=settings.serpapi_key
            )
            logger.info("Using CryptoNewsScraper for crypto macroeconomic news")
        else:
            logger.warning("CryptoNewsScraper not available, will use only FRED data and RAG")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for crypto macro analysis"""
        return """You are a professional cryptocurrency macroeconomic analyst with expertise in:
- Central bank monetary policy impacts on crypto (Fed interest rates, QE, QT)
- Inflation effects on Bitcoin and stablecoins
- Regulatory developments (SEC, CFTC, global regulations)
- Institutional adoption trends
- Macroeconomic indicators affecting crypto markets
- USD strength correlation with crypto
- Risk-on/risk-off market environments
- Global liquidity conditions
- Geopolitical events impacting crypto

Your role is to analyze macroeconomic data and provide insights specifically for cryptocurrency markets.

Provide analysis in JSON format with this exact structure:
{
    "summary": "Brief executive summary focused on crypto impact",
    "monetary_policy_impact": "bullish/bearish/neutral for crypto",
    "regulatory_environment": "favorable/unfavorable/neutral",
    "institutional_adoption_trend": "accelerating/decelerating/stable",
    "crypto_correlation": "risk_on/risk_off/decoupled",
    "key_factors": ["factor1", "factor2", ...],
    "confidence": 0.0-1.0,
    "top_crypto_risks": ["risk1", "risk2", ...],
    "recommended_watchlist": ["BTC", "ETH", ...]
}

IMPORTANT: Only respond with valid JSON. No explanations, no markdown formatting."""
    
    async def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze crypto macroeconomic conditions
        
        Args:
            query: Analysis query
            context: Additional context
            
        Returns:
            Crypto macro analysis results
        """
        try:
            logger.info(f"Crypto Macro Analyst analyzing: {query}")
            
            # Extract asset symbol from context
            asset_symbol = context.get('asset_symbol', '').upper() if context else ''
            
            # Translate query to English if needed
            user_language = context.get('language', 'en') if context else 'en'
            query_in_english = self.translation_service.translate_text(query, src=user_language, dest='en')
            
            # Collect data from multiple sources
            economic_data = await self._collect_economic_data()
            crypto_news_data = await self._collect_crypto_news_data(query_in_english, asset_symbol)
            rag_documents = await self._get_crypto_rag_documents(query_in_english, asset_symbol)
            
            # Generate crypto-specific macro analysis
            analysis_result = await self._generate_crypto_macro_analysis(
                query_in_english,
                asset_symbol,
                economic_data,
                crypto_news_data,
                rag_documents
            )
            
            # Create formatted output
            return self._format_crypto_output(
                analysis_result,
                economic_data,
                rag_documents
            )
            
        except Exception as e:
            logger.error(f"Error in Crypto Macro Analyst: {str(e)}")
            return self._create_crypto_fallback_analysis(query)
    
    async def _collect_economic_data(self) -> Dict[str, Any]:
        """Collect economic data that impacts crypto markets"""
        try:
            # Get key indicators that affect crypto
            indicators = await self.fred_client.get_economic_indicators()
            
            # Focus on indicators that matter most for crypto
            crypto_relevant_indicators = {
                "fed_funds_rate": indicators.get("fed_funds_rate", 5.5),
                "inflation_cpi": indicators.get("inflation_cpi", 324.0),
                "dollar_index": indicators.get("dollar_index", 105.0),
                "treasury_yield_10y": indicators.get("treasury_yield_10y", 4.0),
                "data_quality": indicators.get("data_quality", "unknown"),
                "timestamp": indicators.get("timestamp", "2025-12-04T20:00:00Z")
            }
            
            logger.info(f"Collected {len(crypto_relevant_indicators)} crypto-relevant economic indicators")
            return crypto_relevant_indicators
            
        except Exception as e:
            logger.error(f"Error collecting crypto economic data from FRED: {str(e)}")
            return self._get_crypto_fallback_economic_data()
    
    def _get_crypto_fallback_economic_data(self) -> Dict[str, Any]:
        """Provide fallback economic data for crypto when FRED fails"""
        return {
            "fed_funds_rate": 5.5,
            "inflation_cpi": 324.0,
            "dollar_index": 105.0,
            "treasury_yield_10y": 4.0,
            "data_quality": "estimated_fallback",
            "timestamp": "2025-12-04T20:00:00Z",
            "note": "Fallback data for crypto macro analysis"
        }
    
    async def _collect_crypto_news_data(self, query: str, asset_symbol: str) -> List[Dict]:
        """Collect crypto-specific macroeconomic news"""
        if not self.crypto_scraper:
            return []
        
        try:
            # Run scraper in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Get all news from CryptoNewsScraper
            use_serper = bool(self.crypto_scraper.serper_api_key)
            use_serpapi = bool(self.crypto_scraper.serpapi_key)
            
            all_news = await loop.run_in_executor(
                None,
                self.crypto_scraper.scrape_all,
                use_serper,
                use_serpapi
            )
            
            # Filter for crypto macroeconomic news
            crypto_macro_news = []
            crypto_macro_keywords = [
                'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi',
                'regulation', 'sec', 'cftc', 'digital asset', 'crypto regulation',
                'bitcoin etf', 'institutional', 'adoption', 'blackrock', 'fidelity',
                'monetary policy', 'digital dollar', 'cbdc', 'stablecoin',
                'tether', 'usdc', 'macro', 'economic', 'recession',
                'dollar', 'usd', 'treasury', 'yield', 'liquidity',
                'halving', 'bitcoin halving', 'mining', 'hash rate'
            ]
            
            for source_name, articles in all_news.get('sources', {}).items():
                for article in articles:
                    title = article.get('title', '').lower()
                    snippet = article.get('snippet', '').lower()
                    selftext = article.get('selftext', '').lower()
                    
                    content = f"{title} {snippet} {selftext}"
                    
                    # Check if article contains crypto macroeconomic keywords
                    if any(keyword in content for keyword in crypto_macro_keywords):
                        article['scrape_source'] = source_name
                        article['scrape_timestamp'] = "2025-12-04T20:00:00Z"
                        crypto_macro_news.append(article)
            
            logger.info(f"Found {len(crypto_macro_news)} crypto macroeconomic news articles")
            return crypto_macro_news[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error collecting crypto news from scraper: {str(e)}")
            return []
    
    async def _get_crypto_rag_documents(self, query: str, asset_symbol: str) -> List[Dict]:
        """Get crypto-specific documents from RAG service"""
        try:
            await self.rag_service.initialize()
            
            # Use crypto-specific collection if available
            collection_name = "crypto_macro_data"
            try:
                documents = await self.rag_service.query_collection(
                    query=f"crypto macroeconomic {query}",
                    collection_name=collection_name,
                    n_results=10
                )
            except:
                # Fallback to general macro collection
                documents = await self.rag_service.query_collection(
                    query=f"macroeconomic {query} cryptocurrency",
                    collection_name="macro_data",
                    n_results=10
                )
            
            return documents
        except Exception as e:
            logger.warning(f"Error getting crypto RAG documents: {str(e)}")
            return []
    
    async def _generate_crypto_macro_analysis(
        self,
        query: str,
        asset_symbol: str,
        economic_data: Dict,
        news_data: List[Dict],
        rag_documents: List[Dict]
    ) -> Dict:
        """
        Generate crypto-specific macro analysis using LLM
        """
        try:
            # Prepare crypto-focused prompt
            prompt = self._create_crypto_analysis_prompt(
                query, asset_symbol, economic_data, news_data, rag_documents
            )
            
            # Generate analysis using parent's execute_llm_call with crypto system prompt
            response = await self.execute_llm_call(
                system_prompt=self.get_system_prompt(),
                user_prompt=prompt,
                temperature=0.3  # Lower temperature for more consistent crypto analysis
            )
            
            # Parse JSON response
            analysis_result = self._parse_llm_response(response)
            
            # Enhance with crypto-specific metadata
            enhanced_result = self._enhance_crypto_analysis(
                analysis_result, 
                economic_data,
                len(news_data),
                len(rag_documents),
                asset_symbol
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error generating crypto macro analysis: {str(e)}")
            return self._create_crypto_fallback_macro_analysis(asset_symbol)
    
    def _create_crypto_analysis_prompt(
        self,
        query: str,
        asset_symbol: str,
        economic_data: Dict,
        news_data: List[Dict],
        rag_documents: List[Dict]
    ) -> str:
        """
        Create crypto-focused prompt for LLM analysis
        """
        # Format economic data for crypto analysis
        econ_summary = [
            f"Federal Funds Rate: {economic_data.get('fed_funds_rate', 'N/A')}%",
            f"Inflation (CPI): {economic_data.get('inflation_cpi', 'N/A')}",
            f"Dollar Index (DXY): {economic_data.get('dollar_index', 'N/A')}",
            f"10-Year Treasury Yield: {economic_data.get('treasury_yield_10y', 'N/A')}%",
            f"Data Quality: {economic_data.get('data_quality', 'unknown')}"
        ]
        
        # Format crypto news
        news_summary = []
        for i, article in enumerate(news_data[:5], 1):
            title = article.get('title', 'No title')
            news_summary.append(f"{i}. {title}")
            
            snippet = article.get('snippet', '')
            if snippet:
                news_summary.append(f"   Summary: {snippet[:150]}...")
            
            source = article.get('source', article.get('scrape_source', 'Unknown'))
            news_summary.append(f"   Source: {source}")
            news_summary.append("")
        
        # Create crypto-focused prompt
        prompt = f"""Analyze the cryptocurrency macroeconomic conditions for {asset_symbol if asset_symbol else 'crypto markets'} based on the following data:

QUERY: {query}

KEY ECONOMIC INDICATORS (Crypto-Relevant):
{chr(10).join(econ_summary) if econ_summary else "- No economic indicators available"}

RECENT CRYPTO MACRO NEWS:
{"- No recent crypto macroeconomic news available" if not news_summary else chr(10).join(news_summary)}

CRYPTO MACROECONOMIC CONTEXT:
{"- No historical crypto macroeconomic context available" if not rag_documents else f"Found {len(rag_documents)} relevant crypto documents"}

ANALYSIS FOCUS (CRYPTO-SPECIFIC):
1. How do current interest rates affect crypto as an alternative asset?
2. What is the regulatory environment impact on crypto markets?
3. How is institutional adoption trending?
4. Is crypto behaving as a risk-on or risk-off asset?
5. What are the top risks for crypto in current macroeconomic conditions?
6. Which cryptocurrencies are most affected by current macro conditions?
7. Provide confidence score based on data quality.

Respond with JSON only, using the exact crypto-focused format specified in the system prompt."""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured JSON for crypto analysis"""
        try:
            response = response.strip()
            
            # Handle markdown code blocks
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate required fields for crypto analysis
            required_fields = [
                'summary', 'monetary_policy_impact', 'regulatory_environment',
                'institutional_adoption_trend', 'crypto_correlation'
            ]
            
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing required field in crypto LLM response: {field}")
                    if field == "summary":
                        result[field] = ""
                    elif field == "monetary_policy_impact":
                        result[field] = "neutral"
                    elif field == "regulatory_environment":
                        result[field] = "neutral"
                    elif field == "institutional_adoption_trend":
                        result[field] = "stable"
                    elif field == "crypto_correlation":
                        result[field] = "risk_on"
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse crypto LLM response as JSON: {e}")
            
            return {
                "summary": "Failed to parse cryptocurrency macroeconomic analysis response.",
                "monetary_policy_impact": "neutral",
                "regulatory_environment": "neutral",
                "institutional_adoption_trend": "stable",
                "crypto_correlation": "risk_on",
                "key_factors": ["Data parsing error"],
                "confidence": 0.3,
                "top_crypto_risks": ["Analysis quality compromised"],
                "recommended_watchlist": ["BTC", "ETH"]
            }
    
    def _enhance_crypto_analysis(
        self, 
        analysis_result: Dict, 
        economic_data: Dict,
        news_count: int,
        rag_count: int,
        asset_symbol: str = ""
    ) -> Dict:
        """Enhance crypto analysis with additional metrics"""
        
        # Calculate crypto data quality score
        econ_indicators_count = len([k for k in economic_data.keys() if k not in ['data_quality', 'timestamp', 'note']])
        crypto_data_quality = min(1.0, (econ_indicators_count * 0.4 + news_count * 0.4 + rag_count * 0.2) / 10)
        
        # Adjust confidence based on crypto data quality
        original_confidence = analysis_result.get("confidence", 0.5)
        enhanced_confidence = original_confidence * 0.6 + crypto_data_quality * 0.4
        
        # Add crypto-specific metadata
        analysis_result["metadata"] = {
            "crypto_data_sources_used": {
                "economic_indicators": econ_indicators_count,
                "crypto_news_articles": news_count,
                "crypto_rag_documents": rag_count
            },
            "crypto_data_quality_score": round(crypto_data_quality, 2),
            "analysis_focus": "cryptocurrency_macroeconomic",
            "target_asset": asset_symbol or "general_crypto",
            "analysis_timestamp": "2025-12-04T20:00:00Z"
        }
        
        analysis_result["confidence"] = round(min(enhanced_confidence, 1.0), 2)
        
        # Ensure recommended_watchlist exists
        if "recommended_watchlist" not in analysis_result:
            analysis_result["recommended_watchlist"] = ["BTC", "ETH", "SOL"]
        
        return analysis_result
    
    def _create_crypto_fallback_macro_analysis(self, asset_symbol: str) -> Dict:
        """Create fallback analysis for crypto when LLM fails"""
        return {
            "summary": f"Limited crypto macroeconomic analysis available for {asset_symbol} due to data constraints.",
            "monetary_policy_impact": "neutral",
            "regulatory_environment": "neutral",
            "institutional_adoption_trend": "stable",
            "crypto_correlation": "risk_on",
            "key_factors": ["Data availability", "Market volatility", "Regulatory uncertainty"],
            "confidence": 0.3,
            "top_crypto_risks": ["Limited data", "Potential inaccuracies", "High volatility"],
            "recommended_watchlist": ["BTC", "ETH", "BNB"],
            "metadata": {
                "crypto_data_sources_used": {"economic_indicators": 0, "crypto_news_articles": 0, "crypto_rag_documents": 0},
                "crypto_data_quality_score": 0.0,
                "fallback_analysis": True,
                "analysis_focus": "cryptocurrency_macroeconomic"
            }
        }
    
    def _format_crypto_output(
        self,
        analysis_result: Dict,
        economic_data: Dict,
        rag_documents: List[Dict]
    ) -> Dict[str, Any]:
        """Format the final output for crypto synthesis agent"""
        
        # Extract detailed analysis from metadata if available
        detailed_analysis = analysis_result.copy()
        metadata = detailed_analysis.pop("metadata", {})
        
        # Get crypto-specific factors
        key_factors = analysis_result.get("key_factors", [])
        if not key_factors and "key_factors" in detailed_analysis:
            key_factors = detailed_analysis.get("key_factors", [])
        
        return {
            "agent_name": self.name,
            "summary": analysis_result.get("summary", ""),
            "confidence": analysis_result.get("confidence", 0.5),
            "key_factors": key_factors,
            "crypto_specific_metrics": {
                "monetary_policy_impact": analysis_result.get("monetary_policy_impact", "neutral"),
                "regulatory_environment": analysis_result.get("regulatory_environment", "neutral"),
                "institutional_adoption_trend": analysis_result.get("institutional_adoption_trend", "stable"),
                "recommended_watchlist": analysis_result.get("recommended_watchlist", ["BTC", "ETH"])
            },
            "data_sources": {
                "economic_data_quality": economic_data.get("data_quality", "unknown"),
                "crypto_rag_documents_count": len(rag_documents),
                "crypto_data_quality_score": metadata.get("crypto_data_quality_score", 0.0)
            },
            "detailed_analysis": detailed_analysis
        }
    
    def _create_crypto_fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Create fallback analysis for crypto when everything fails"""
        return {
            "agent_name": self.name,
            "summary": f"Unable to perform cryptocurrency macroeconomic analysis for '{query}' due to technical issues.",
            "confidence": 0.1,
            "key_factors": ["Technical error", "Data unavailability", "System failure"],
            "crypto_specific_metrics": {
                "monetary_policy_impact": "unknown",
                "regulatory_environment": "unknown",
                "institutional_adoption_trend": "unknown",
                "recommended_watchlist": ["BTC"]
            },
            "data_sources": {
                "economic_data_quality": "unavailable",
                "crypto_rag_documents_count": 0,
                "crypto_data_quality_score": 0.0
            },
            "detailed_analysis": {
                "summary": "Crypto macro analysis failed due to technical issues.",
                "monetary_policy_impact": "unknown",
                "regulatory_environment": "unknown",
                "institutional_adoption_trend": "unknown",
                "crypto_correlation": "unknown",
                "key_factors": ["Technical error"],
                "confidence": 0.1,
                "top_crypto_risks": ["System failure", "Data unavailability", "Analysis error"]
            }
        }