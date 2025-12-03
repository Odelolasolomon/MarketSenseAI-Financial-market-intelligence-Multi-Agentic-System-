"""Background Data Collector Service """

import asyncio
from typing import List
from datetime import datetime
import json
from src.adapters.external.binance_client import BinanceClient
from src.adapters.external.fred_client import FREDClient
from src.adapters.external.newsapi_client import NewsAPIClient
from src.infrastructure.cache import get_cache
from src.config.constants import CRYPTO_PAIRS
from src.utilities.logger import get_logger

logger = get_logger(__name__)  # Fixed: changed _name_ to __name__


class DataCollector:
    """Collects and indexes market data in background"""
    
    def __init__(self, rag_service=None):  # Fixed: changed _init_ to __init__
        self.rag_service = rag_service  # Accept RAGService as parameter
        self.cache = get_cache()
        self.running = False
    
    def set_rag_service(self, rag_service):
        """Set RAG service after initialization"""
        self.rag_service = rag_service
    
    async def collect_crypto_data(self):
        """Collect cryptocurrency data"""
        try:
            logger.info("Collecting crypto data...")
            
            if not self.rag_service:
                logger.warning("RAG service not set, skipping crypto data collection")
                return
            
            async with BinanceClient() as binance:
                for pair in CRYPTO_PAIRS[:5]:  # Top 5 pairs
                    try:
                        symbol = pair.replace("/", "")
                        ticker = await binance.get_24h_ticker(symbol)
                        
                        crypto_data = {
                            "symbol": pair,
                            "price": float(ticker["lastPrice"]),
                            "change_24h": float(ticker["priceChangePercent"]),
                            "volume": float(ticker["volume"]),
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Update RAG knowledge base
                        await self.rag_service.update_crypto_knowledge(crypto_data)
                        
                        await asyncio.sleep(0.5)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Error collecting data for {pair}: {str(e)}")
            
            logger.info("Crypto data collection completed")
            
        except Exception as e:
            logger.error(f"Error in crypto data collection: {str(e)}")
    
    async def collect_economic_data(self):
        """Collect macroeconomic data"""
        try:
            logger.info("Collecting economic data...")
            
            if not self.rag_service:
                logger.warning("RAG service not set, skipping economic data collection")
                return
            
            async with FREDClient() as fred:
                economic_data = await fred.get_economic_indicators()
                
                # Update RAG knowledge base
                await self.rag_service.update_macro_knowledge(economic_data)
            
            logger.info("Economic data collection completed")
            
        except Exception as e:
            logger.error(f"Error in economic data collection: {str(e)}")
    
    async def collect_news_data(self):
        """Collect news articles"""
        try:
            logger.info("Collecting news data...")
            
            if not self.rag_service:
                logger.warning("RAG service not set, skipping news data collection")
                return
            
            async with NewsAPIClient() as news_api:
                # Crypto news
                crypto_articles = await news_api.search_crypto_news("Bitcoin", days=1, page_size=10)
                
                # Business news
                business_result = await news_api.get_top_headlines(
                    category="business",
                    page_size=10
                )
                business_articles = business_result.get("articles", [])
                
                all_articles = crypto_articles + business_articles
                
                # Update RAG knowledge base
                await self.rag_service.update_news_knowledge(all_articles)
            
            logger.info("News data collection completed")
            
        except Exception as e:
            logger.error(f"Error in news data collection: {str(e)}")
    
    async def run_collection_cycle(self):
        """Run one complete data collection cycle"""
        logger.info("=== Starting data collection cycle ===")
        start_time = datetime.now()
        
        # Run collections in parallel
        await asyncio.gather(
            self.collect_crypto_data(),
            self.collect_economic_data(),
            self.collect_news_data(),
            return_exceptions=True
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Data collection cycle completed in {duration:.2f}s ===")
    
    async def start(self, interval: int = 3600):
        """
        Start continuous data collection
        
        Args:
            interval: Collection interval in seconds
        """
        self.running = True
        logger.info(f"Data collector started (interval: {interval}s)")
        
        while self.running:
            try:
                await self.run_collection_cycle()
                logger.info(f"Waiting {interval} seconds until next cycle...")
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in collection cycle: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop data collection"""
        self.running = False
        logger.info("Data collector stopped")