"""
Data Service - Coordinates data collection from multiple sources
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.adapters.external.binance_client import BinanceClient
from src.adapters.external.coingecko_client import CoinGeckoClient
from src.adapters.external.fred_client import FREDClient
from src.domain.entities.market_data import MarketData
from src.domain.entities.asset import Asset
from src.config.constants import AssetType 
from src.infrastructure.cache import get_cache, CACHE_MARKET_DATA
from src.utilities.logger import get_logger

logger = get_logger(__name__)


class DataService:
    """Service for collecting and managing market data"""
    
    def __init__(self):
        self.cache = get_cache()
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get current market data for an asset
        
        Args:
            symbol: Asset symbol
            
        Returns:
            MarketData entity or None
        """
        try:
            # Check cache first
            cache_key = f"market:{symbol}"
            cached = self.cache.get(cache_key, prefix=CACHE_MARKET_DATA)
            
            if cached:
                logger.info(f"Cache hit for market data: {symbol}")
                return MarketData.from_dict(cached)
            
            # Determine asset type and fetch data
            if "/" in symbol or symbol.endswith("USDT"):
                market_data = await self._get_crypto_data(symbol)
            else:
                market_data = await self._get_crypto_data(symbol)  # Default to crypto
            
            # Cache result
            if market_data:
                self.cache.set(
                    cache_key,
                    market_data.to_dict(),
                    ttl=300,  # 5 minutes
                    prefix=CACHE_MARKET_DATA
                )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None
    
    async def _get_crypto_data(self, symbol: str) -> Optional[MarketData]:
        """Get cryptocurrency market data"""
        try:
            # Normalize symbol
            clean_symbol = symbol.replace("/", "").replace("USDT", "")
            
            async with BinanceClient() as binance:
                ticker = await binance.get_24h_ticker(f"{clean_symbol}USDT")
                
                market_data = MarketData(
                    asset_symbol=symbol,
                    timestamp=datetime.now(),
                    price=float(ticker['lastPrice']),
                    open_price=float(ticker['openPrice']),
                    high_price=float(ticker['highPrice']),
                    low_price=float(ticker['lowPrice']),
                    close_price=float(ticker['lastPrice']),
                    volume=float(ticker['volume']),
                    volume_quote=float(ticker['quoteVolume']),
                    change_24h=float(ticker['priceChangePercent']),
                    data_source="binance"
                )
                
                return market_data
                
        except Exception as e:
            logger.error(f"Error getting crypto data: {str(e)}")
            return None
    
    async def get_trending_assets(self) -> Dict[str, Any]:
        """
        Get trending cryptocurrencies
        
        Returns:
            Dictionary with trending assets info
        """
        try:
            async with CoinGeckoClient() as coingecko:
                trending = await coingecko.get_trending()
                global_data = await coingecko.get_global_data()
                
                return {
                    "trending_coins": trending.get("coins", [])[:10],
                    "global_data": global_data.get("data", {}),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting trending assets: {str(e)}")
            return {"trending_coins": [], "global_data": {}}
    
    async def get_historical_data(
        self,
        symbol: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data
        
        Args:
            symbol: Asset symbol
            days: Number of days of history
            
        Returns:
            List of historical data points
        """
        try:
            clean_symbol = symbol.replace("/", "")
            
            async with BinanceClient() as binance:
                klines = await binance.get_klines(
                    f"{clean_symbol}USDT",
                    interval="1d",
                    limit=days
                )
                
                historical = []
                for kline in klines:
                    historical.append({
                        "timestamp": datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5])
                    })
                
                return historical
                
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return []
    
    async def get_multiple_assets(
        self,
        symbols: List[str]
    ) -> Dict[str, Optional[MarketData]]:
        """
        Get market data for multiple assets
        
        Args:
            symbols: List of asset symbols
            
        Returns:
            Dictionary mapping symbols to market data
        """
        import asyncio
        
        tasks = [self.get_market_data(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }

