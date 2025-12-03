"""
Technical Analyst Agent - Analyzes price action and technical indicators
"""
import json
from typing import Dict, Any, Optional
from src.application.agents.base_agent import BaseAgent
from src.application.services.rag_service import RAGService
from src.application.services.tts_service import TTSService
from src.application.services.speech_service import SpeechService
from src.application.services.translation_service import TranslationService
from src.adapters.external.binance_client import BinanceClient
from src.adapters.external.coingecko_client import CoinGeckoClient 
from src.utilities.logger import get_logger 
import pandas as pd
from ta import momentum, trend, volatility
from datetime import datetime, timedelta

logger = get_logger(__name__)


class TechnicalAnalyst(BaseAgent):
    """Agent specialized in technical analysis"""
    
    def __init__(self):
        super().__init__(
            name="Technical Analyst",
            description="Analyzes price action, technical indicators, and on-chain metrics"
        )
        self.rag_service = RAGService()
        self.tts_service = TTSService()
        self.speech_service = SpeechService()
        self.translation_service = TranslationService()
    
    def get_system_prompt(self) -> str:
        """Get system prompt for technical analysis"""
        return """You are an expert technical analyst specializing in:
- Price action and chart patterns
- Technical indicators (RSI, MACD, Moving Averages, Bollinger Bands)
- Support and resistance levels
- Trend analysis and momentum
- On-chain metrics for cryptocurrencies (when applicable)

Provide analysis in JSON format with:
{
    "summary": "Brief technical summary",
    "trend": "bullish/bearish/neutral",
    "momentum": "strong/moderate/weak",
    "support_levels": [level1, level2, ...],
    "resistance_levels": [level1, level2, ...],
    "technical_signals": {
        "rsi": "overbought/oversold/neutral",
        "macd": "bullish/bearish/neutral",
        "moving_averages": "golden_cross/death_cross/neutral"
    },
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
        Perform technical analysis
        
        Args:
            query: Analysis query
            context: Additional context with asset info
            
        Returns:
            Technical analysis results
        """
        try:
            # Translate query to English if needed
            user_language = context.get("language", "en") if context else "en"
            query_in_english = self.translation_service.translate_text(query, src=user_language, dest="en")
            
            asset_symbol = context.get("asset_symbol", "BTC") if context else "BTC"
            logger.info(f"Technical Analyst analyzing: {asset_symbol}")
            
            # Retrieve context using RAGService
            documents = await self.rag_service.query_collection(query_in_english, "crypto")
            logger.info(f"Retrieved {len(documents)} documents for query: {query_in_english}")
            
            # Collect price data and calculate indicators
            technical_data = await self._collect_technical_data(asset_symbol)
            
            # Format prompt
            user_prompt = f"""Analyze technical indicators for {asset_symbol}: {query_in_english}

Technical Data:
{json.dumps(technical_data, indent=2)}

Retrieved Context:
{json.dumps(documents, indent=2)}

Provide comprehensive technical analysis with specific price levels."""
            
            # Execute LLM call
            response = await self.execute_llm_call(
                system_prompt=self.get_system_prompt(),
                user_prompt=user_prompt
            )
            
            # Parse response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                analysis = {
                    "summary": response,
                    "confidence": 0.6,
                    "key_factors": []
                }
            
            # Translate response back to user's language
            translated_response = self.translation_service.translate_text(
                analysis.get("summary", ""), src="en", dest=user_language
            )
            analysis["summary"] = translated_response
            
            # Convert response to speech if requested
            if context.get("audio_output", False):
                audio_path = self.tts_service.text_to_speech(translated_response, language=user_language)
                analysis["audio_path"] = audio_path
            
            return self.format_output(
                analysis=analysis,
                confidence=analysis.get("confidence", 0.7),
                key_factors=analysis.get("key_factors", [])
            )
            
        except Exception as e:
            logger.error(f"Error in Technical Analyst: {str(e)}")
            return {
                "agent_name": self.name,
                "error": str(e),
                "confidence": 0.0
            }
    
    async def _collect_technical_data(self, symbol: str) -> Dict[str, Any]:
        """Collect and calculate technical indicators with fallback to CoinGecko"""
        try:
            # Try Binance first
            return await self._get_binance_data(symbol)
        except Exception as binance_error:
            logger.warning(f"Binance data collection failed: {str(binance_error)}, falling back to CoinGecko")
            try:
                return await self._get_coingecko_data(symbol)
            except Exception as coingecko_error:
                logger.error(f"CoinGecko data collection also failed: {str(coingecko_error)}")
                return {}
    
    async def _get_binance_data(self, symbol: str) -> Dict[str, Any]:
        """Get data from Binance and calculate indicators"""
        async with BinanceClient() as binance:
            ticker = await binance.get_24h_ticker(f"{symbol}USDT")
            klines = await binance.get_klines(f"{symbol}USDT", interval="1d", limit=200)
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Calculate indicators
        indicators = self._calculate_indicators(df)
        
        current_price = float(ticker['lastPrice'])
        
        return {
            "source": "binance",
            "current_price": current_price,
            "24h_change": float(ticker['priceChangePercent']),
            "24h_volume": float(ticker['volume']),
            "24h_high": float(ticker['highPrice']),
            "24h_low": float(ticker['lowPrice']),
            "technical_indicators": indicators
        }
    
    async def _get_coingecko_data(self, symbol: str) -> Dict[str, Any]:
        """Get data from CoinGecko and calculate indicators"""
        async with CoinGeckoClient() as coingecko:
            # Convert symbol to CoinGecko ID
            coin_id = coingecko.normalize_symbol(symbol)
            
            # Get current price and 24h data
            simple_price = await coingecko.get_simple_price(
                coin_ids=[coin_id],
                include_24h_change=True,
                include_market_cap=True,
                include_24h_volume=True
            )
            
            # Get historical data for technical indicators
            market_chart = await coingecko.get_market_chart(
                coin_id=coin_id,
                vs_currency="usd",
                days=200
            )
            
            # Get comprehensive coin data
            coin_data = await coingecko.get_coin_data(coin_id)
        
        # Extract price data
        prices = market_chart.get('prices', [])
        if not prices:
            raise ValueError("No price data available from CoinGecko")
        
        # Convert to DataFrame
        df = pd.DataFrame(prices, columns=['timestamp', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # For more accurate indicators, we need OHLC data
        # CoinGecko's market_chart only provides closing prices
        # We'll approximate high/low using rolling windows
        df['high'] = df['close'].rolling(window=24, min_periods=1).max()
        df['low'] = df['close'].rolling(window=24, min_periods=1).min()
        df['open'] = df['close'].shift(1).fillna(df['close'])
        
        # Calculate indicators
        indicators = self._calculate_indicators(df)
        
        # Extract current data
        coin_price_data = simple_price.get(coin_id, {})
        current_price = coin_price_data.get('usd', 0)
        price_change_24h = coin_price_data.get('usd_24h_change', 0)
        volume_24h = coin_price_data.get('usd_24h_vol', 0)
        
        # Get 24h high/low from coin data
        market_data = coin_data.get('market_data', {})
        high_24h = market_data.get('high_24h', {}).get('usd', current_price)
        low_24h = market_data.get('low_24h', {}).get('usd', current_price)
        
        return {
            "source": "coingecko",
            "current_price": current_price,
            "24h_change": price_change_24h,
            "24h_volume": volume_24h,
            "24h_high": high_24h,
            "24h_low": low_24h,
            "market_cap": coin_price_data.get('usd_market_cap', 0),
            "technical_indicators": indicators,
            "note": "Technical indicators calculated from daily closing prices (CoinGecko limitation)"
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical indicators from DataFrame"""
        try:
            close = df['close']
            
            # RSI
            rsi_indicator = momentum.RSIIndicator(close)
            rsi = rsi_indicator.rsi().iloc[-1]
            
            # MACD
            macd_indicator = trend.MACD(close)
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            
            # Moving Averages
            sma_50 = trend.SMAIndicator(close, window=min(50, len(close))).sma_indicator().iloc[-1]
            sma_200 = trend.SMAIndicator(close, window=min(200, len(close))).sma_indicator().iloc[-1]
            
            # Bollinger Bands
            bb = volatility.BollingerBands(close)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            
            return {
                "rsi": round(float(rsi), 2) if pd.notna(rsi) else None,
                "macd": round(float(macd), 2) if pd.notna(macd) else None,
                "macd_signal": round(float(macd_signal), 2) if pd.notna(macd_signal) else None,
                "sma_50": round(float(sma_50), 2) if pd.notna(sma_50) else None,
                "sma_200": round(float(sma_200), 2) if pd.notna(sma_200) else None,
                "bb_upper": round(float(bb_upper), 2) if pd.notna(bb_upper) else None,
                "bb_lower": round(float(bb_lower), 2) if pd.notna(bb_lower) else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return {}