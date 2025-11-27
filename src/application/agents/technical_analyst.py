"""
Technical Analyst Agent - Analyzes price action and technical indicators
"""
import json
from typing import Dict, Any, Optional
from src.application.agents.base_agent import BaseAgent
from src.adapters.external.binance_client import BinanceClient
from src.adapters.external.coingecko_client import CoinGeckoClient
from src.utilities.logger import get_logger
import pandas as pd
from ta import momentum, trend, volatility

logger = get_logger(__name__)


class TechnicalAnalyst(BaseAgent):
    """Agent specialized in technical analysis"""
    
    def __init__(self):
        super().__init__(
            name="Technical Analyst",
            description="Analyzes price action, technical indicators, and on-chain metrics"
        )
    
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
            asset_symbol = context.get("asset_symbol", "BTC") if context else "BTC"
            logger.info(f"Technical Analyst analyzing: {asset_symbol}")
            
            # Collect price data and calculate indicators
            technical_data = await self._collect_technical_data(asset_symbol)
            
            # Format prompt
            user_prompt = f"""Analyze technical indicators for {asset_symbol}: {query}

Technical Data:
{json.dumps(technical_data, indent=2)}

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
        """Collect and calculate technical indicators"""
        try:
            # Get price data from Binance
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
            close = df['close']
            
            # RSI
            rsi_indicator = momentum.RSIIndicator(close)
            rsi = rsi_indicator.rsi().iloc[-1]
            
            # MACD
            macd_indicator = trend.MACD(close)
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            
            # Moving Averages
            sma_50 = trend.SMAIndicator(close, window=50).sma_indicator().iloc[-1]
            sma_200 = trend.SMAIndicator(close, window=200).sma_indicator().iloc[-1]
            
            # Bollinger Bands
            bb = volatility.BollingerBands(close)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            
            current_price = float(ticker['lastPrice'])
            
            return {
                "current_price": current_price,
                "24h_change": float(ticker['priceChangePercent']),
                "24h_volume": float(ticker['volume']),
                "24h_high": float(ticker['highPrice']),
                "24h_low": float(ticker['lowPrice']),
                "technical_indicators": {
                    "rsi": round(rsi, 2),
                    "macd": round(macd, 2),
                    "macd_signal": round(macd_signal, 2),
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2),
                    "bb_upper": round(bb_upper, 2),
                    "bb_lower": round(bb_lower, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error collecting technical data: {str(e)}")
            return {}