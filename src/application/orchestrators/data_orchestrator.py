"""
Complete Data Collection Orchestrator
Coordinates all data sources and updates RAG service
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import json
from dataclasses import dataclass, asdict
from enum import Enum

from src.utilities.logger import get_logger
from src.application.services.rag_service import RAGService
from src.config.constants import (
    CHROMA_COLLECTION_MACRO,
    CHROMA_COLLECTION_CRYPTO,
    CHROMA_COLLECTION_NEWS
)

logger = get_logger(__name__)


class UpdatePriority(Enum):
    """Priority levels for data updates"""
    CRITICAL = "critical"  # Update every 5 minutes
    HIGH = "high"         # Update every 15 minutes
    MEDIUM = "medium"     # Update every hour
    LOW = "low"          # Update every 6 hours


@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    enabled: bool
    priority: UpdatePriority
    scraper_type: str  # 'basic', 'deep', 'api'
    urls: List[str]
    collection: str
    last_update: Optional[str] = None
    success_rate: float = 1.0
    total_fetches: int = 0


class DataOrchestrator:
    """Orchestrates all data collection and RAG updates"""
    
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.scheduler = AsyncIOScheduler()
        self.running = False
        
        # Statistics tracking
        self.stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "total_documents": 0,
            "last_full_update": None,
            "source_stats": {}
        }
        
        # Configure data sources
        self.sources = self._initialize_sources()
    
    def _initialize_sources(self) -> Dict[str, DataSourceConfig]:
        """Initialize all data source configurations"""
        return {
            "reuters_forex": DataSourceConfig(
                name="Reuters Forex",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="basic",
                urls=[
                    "https://www.reuters.com/markets/currencies/",
                    "https://www.reuters.com/markets/global-market-data/"
                ],
                collection=CHROMA_COLLECTION_NEWS
            ),
            "reuters_stocks": DataSourceConfig(
                name="Reuters Stocks",
                enabled=True,
                priority=UpdatePriority.MEDIUM,
                scraper_type="basic",
                urls=["https://www.reuters.com/markets/stocks/us/"],
                collection=CHROMA_COLLECTION_NEWS
            ),
            "bloomberg_fx": DataSourceConfig(
                name="Bloomberg FX",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="deep",
                urls=[
                    "https://www.bloomberg.com/fx-center",
                    "https://www.bloomberg.com/markets/currencies"
                ],
                collection=CHROMA_COLLECTION_MACRO
            ),
            "bloomberg_africa": DataSourceConfig(
                name="Bloomberg Africa",
                enabled=True,
                priority=UpdatePriority.MEDIUM,
                scraper_type="basic",
                urls=["https://www.bloomberg.com/africa"],
                collection=CHROMA_COLLECTION_NEWS
            ),
            "coindesk_markets": DataSourceConfig(
                name="CoinDesk Markets",
                enabled=True,
                priority=UpdatePriority.CRITICAL,
                scraper_type="deep",
                urls=[
                    "https://www.coindesk.com/markets",
                    "https://www.coindesk.com/price"
                ],
                collection=CHROMA_COLLECTION_CRYPTO
            ),
            "coindesk_crypto": DataSourceConfig(
                name="CoinDesk Crypto News",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="basic",
                urls=[
                    "https://www.coindesk.com/tag/bitcoin",
                    "https://www.coindesk.com/tag/ethereum",
                    "https://www.coindesk.com/tag/xrp",
                    "https://www.coindesk.com/tag/solana"
                ],
                collection=CHROMA_COLLECTION_CRYPTO
            ),
            "financefeeds": DataSourceConfig(
                name="Finance Feeds",
                enabled=True,
                priority=UpdatePriority.MEDIUM,
                scraper_type="basic",
                urls=["https://financefeeds.com/category/market-news/"],
                collection=CHROMA_COLLECTION_NEWS
            ),
            "fxcoinz_crypto": DataSourceConfig(
                name="FXCoinz Crypto",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="basic",
                urls=[
                    "https://www.fxcoinz.com/news/crypto-news",
                    "https://www.fxcoinz.com/forecasts/crypto-forecasts"
                ],
                collection=CHROMA_COLLECTION_CRYPTO
            ),
            "fxcoinz_forex": DataSourceConfig(
                name="FXCoinz Forex",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="basic",
                urls=[
                    "https://www.fxcoinz.com/news/forex-news",
                    "https://www.fxcoinz.com/forecasts/forex-forecasts"
                ],
                collection=CHROMA_COLLECTION_MACRO
            ),
            "cryptofax": DataSourceConfig(
                name="CryptoFax Report",
                enabled=True,
                priority=UpdatePriority.MEDIUM,
                scraper_type="basic",
                urls=["https://www.cryptofaxreport.com/explore"],
                collection=CHROMA_COLLECTION_CRYPTO
            ),
            "newsnow_crypto": DataSourceConfig(
                name="NewsNow Crypto",
                enabled=True,
                priority=UpdatePriority.HIGH,
                scraper_type="basic",
                urls=["https://www.newsnow.com/us/Business/Cryptocurrencies"],
                collection=CHROMA_COLLECTION_CRYPTO
            ),
            "market_data_api": DataSourceConfig(
                name="Market Data APIs",
                enabled=True,
                priority=UpdatePriority.CRITICAL,
                scraper_type="api",
                urls=[],  # Uses MarketDataAggregator
                collection=CHROMA_COLLECTION_MACRO
            )
        }
    
    async def update_source(self, source_key: str) -> Dict[str, Any]:
        """Update a specific data source"""
        if source_key not in self.sources:
            logger.error(f"Unknown source: {source_key}")
            return {"success": False, "error": "Unknown source"}
        
        source = self.sources[source_key]
        
        if not source.enabled:
            logger.info(f"Source {source.name} is disabled, skipping")
            return {"success": False, "error": "Source disabled"}
        
        logger.info(f"Updating {source.name}...")
        
        start_time = datetime.now()
        result = {
            "source": source.name,
            "started_at": start_time.isoformat(),
            "success": False,
            "documents_added": 0,
            "errors": []
        }
        
        try:
            documents = []
            
            # Route to appropriate scraper
            if source.scraper_type == "api":
                documents = await self._fetch_api_data(source)
            elif source.scraper_type == "deep":
                documents = await self._fetch_deep_scraper(source)
            else:  # basic
                documents = await self._fetch_basic_scraper(source)
            
            # Add to RAG if we got documents
            if documents:
                success = await self.rag_service.add_documents(
                    documents,
                    source.collection
                )
                
                if success:
                    result["success"] = True
                    result["documents_added"] = len(documents)
                    
                    # Update source stats
                    source.last_update = datetime.now().isoformat()
                    source.total_fetches += 1
                    
                    # Update global stats
                    self.stats["successful_updates"] += 1
                    self.stats["total_documents"] += len(documents)
                    
                    if source.name not in self.stats["source_stats"]:
                        self.stats["source_stats"][source.name] = {
                            "total_documents": 0,
                            "last_update": None,
                            "update_count": 0
                        }
                    
                    self.stats["source_stats"][source.name]["total_documents"] += len(documents)
                    self.stats["source_stats"][source.name]["last_update"] = datetime.now().isoformat()
                    self.stats["source_stats"][source.name]["update_count"] += 1
                else:
                    result["errors"].append("Failed to add documents to RAG")
                    self.stats["failed_updates"] += 1
            else:
                result["errors"].append("No documents fetched")
                self.stats["failed_updates"] += 1
            
            result["completed_at"] = datetime.now().isoformat()
            result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            
            self.stats["total_updates"] += 1
            
            logger.info(f"✓ {source.name}: {len(documents)} documents in {result['duration_seconds']:.2f}s")
            
        except Exception as e:
            logger.error(f"Error updating {source.name}: {str(e)}")
            result["errors"].append(str(e))
            self.stats["failed_updates"] += 1
        
        return result
    
    async def _fetch_api_data(self, source: DataSourceConfig) -> List[Dict[str, Any]]:
        """Fetch data using MarketDataAggregator API"""
        # Since we don't have MarketDataAggregator in data_collector.py,
        # we'll use the existing APIs directly or create a simple implementation
        
        documents = []
        
        try:
            # For now, we'll create a simple implementation
            # You can expand this later with actual API calls
            import aiohttp
            from datetime import datetime
            
            async with aiohttp.ClientSession() as session:
                # Forex data from ExchangeRate-API
                forex_url = "https://api.exchangerate-api.com/v4/latest/USD"
                async with session.get(forex_url) as response:
                    if response.status == 200:
                        forex_data = await response.json()
                        documents.append({
                            "text": f"Forex Rates Update: {datetime.now()}\n" +
                                    json.dumps(forex_data, indent=2),
                            "metadata": {
                                "type": "forex_data",
                                "source": "ExchangeRate API",
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                
                # Crypto data from CoinGecko
                crypto_symbols = ["bitcoin", "ethereum", "binancecoin", "ripple", "cardano"]
                crypto_url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(crypto_symbols)}&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true"
                async with session.get(crypto_url) as response:
                    if response.status == 200:
                        crypto_data = await response.json()
                        for symbol, data in crypto_data.items():
                            documents.append({
                                "text": f"Crypto: {symbol}\n" +
                                        f"Price: ${data.get('usd', 0):,.2f}\n" +
                                        f"Market Cap: ${data.get('usd_market_cap', 0):,.0f}",
                                "metadata": {
                                    "type": "crypto_price",
                                    "symbol": symbol,
                                    "source": "CoinGecko",
                                    "timestamp": datetime.now().isoformat()
                                }
                            })
        
        except Exception as e:
            logger.error(f"Error fetching API data: {str(e)}")
        
        return documents
    
    async def _fetch_basic_scraper(self, source: DataSourceConfig) -> List[Dict[str, Any]]:
        """Fetch using basic NewsAggregator"""
        from src.application.services.news_aggregator import NewsAggregator  # Import the artifact we created
        
        documents = []
        
        async with NewsAggregator(max_concurrent=5) as aggregator:
            for url in source.urls:
                try:
                    html = await aggregator._fetch_page(url)
                    if html:
                        # Use generic parser
                        articles = await aggregator._parse_generic(url, html)
                        documents.extend(aggregator.prepare_for_rag(articles))
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error fetching {url}: {str(e)}")
        
        return documents
    
    async def _fetch_deep_scraper(self, source: DataSourceConfig) -> List[Dict[str, Any]]:
        """Fetch using DeepContentScraper for JavaScript sites"""
        from src.application.services.deep_scraper import DeepContentScraper
        
        documents = []
        
        async with DeepContentScraper(headless=True) as scraper:
            for url in source.urls:
                try:
                    result = await scraper.scrape_dynamic_site(url, scroll_to_bottom=True)
                    
                    if result["success"]:
                        # Convert to document format
                        documents.append({
                            "text": f"{result['title']}\n\n{result['text'][:5000]}",
                            "metadata": {
                                "source": source.name,
                                "url": url,
                                "type": "scraped_content",
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                    
                    await asyncio.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error deep scraping {url}: {str(e)}")
        
        return documents
    
    async def update_all_sources(self) -> Dict[str, Any]:
        """Update all enabled sources"""
        logger.info("Starting full data update...")
        
        start_time = datetime.now()
        results = []
        
        # Group sources by priority
        priority_groups = {
            UpdatePriority.CRITICAL: [],
            UpdatePriority.HIGH: [],
            UpdatePriority.MEDIUM: [],
            UpdatePriority.LOW: []
        }
        
        for key, source in self.sources.items():
            if source.enabled:
                priority_groups[source.priority].append(key)
        
        # Update in priority order
        for priority in [UpdatePriority.CRITICAL, UpdatePriority.HIGH, 
                        UpdatePriority.MEDIUM, UpdatePriority.LOW]:
            
            sources = priority_groups[priority]
            if sources:
                logger.info(f"Updating {len(sources)} {priority.value} priority sources...")
                
                # Update concurrently within priority group
                tasks = [self.update_source(key) for key in sources]
                priority_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in priority_results:
                    if isinstance(result, Exception):
                        results.append({"error": str(result)})
                    else:
                        results.append(result)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            "started_at": start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": duration,
            "sources_updated": len([r for r in results if r.get("success")]),
            "total_sources": len(results),
            "total_documents": sum(r.get("documents_added", 0) for r in results),
            "results": results
        }
        
        self.stats["last_full_update"] = datetime.now().isoformat()
        
        logger.info(f"Full update complete: {summary['sources_updated']}/{summary['total_sources']} sources, "
                   f"{summary['total_documents']} documents in {duration:.2f}s")
        
        return summary
    
    def setup_schedule(self):
        """Setup automatic update schedule"""
        logger.info("Setting up data collection schedule...")
        
        # Critical updates - every 5 minutes
        self.scheduler.add_job(
            self._update_critical_sources,
            CronTrigger(minute='*/5'),
            id='critical_updates',
            replace_existing=True
        )
        
        # High priority - every 15 minutes
        self.scheduler.add_job(
            self._update_high_priority_sources,
            CronTrigger(minute='*/15'),
            id='high_priority_updates',
            replace_existing=True
        )
        
        # Medium priority - hourly
        self.scheduler.add_job(
            self._update_medium_priority_sources,
            CronTrigger(minute='0'),
            id='medium_priority_updates',
            replace_existing=True
        )
        
        # Low priority - every 6 hours
        self.scheduler.add_job(
            self._update_low_priority_sources,
            CronTrigger(hour='*/6', minute='0'),
            id='low_priority_updates',
            replace_existing=True
        )
        
        # Full system update - daily at 2 AM
        self.scheduler.add_job(
            self.update_all_sources,
            CronTrigger(hour='2', minute='0'),
            id='daily_full_update',
            replace_existing=True
        )
        
        logger.info("Schedule configured successfully")
    
    async def _update_critical_sources(self):
        """Update critical priority sources"""
        await self._update_by_priority(UpdatePriority.CRITICAL)
    
    async def _update_high_priority_sources(self):
        """Update high priority sources"""
        await self._update_by_priority(UpdatePriority.HIGH)
    
    async def _update_medium_priority_sources(self):
        """Update medium priority sources"""
        await self._update_by_priority(UpdatePriority.MEDIUM)
    
    async def _update_low_priority_sources(self):
        """Update low priority sources"""
        await self._update_by_priority(UpdatePriority.LOW)
    
    async def _update_by_priority(self, priority: UpdatePriority):
        """Update all sources with given priority"""
        sources = [key for key, src in self.sources.items() 
                  if src.enabled and src.priority == priority]
        
        if sources:
            logger.info(f"Updating {len(sources)} {priority.value} priority sources")
            tasks = [self.update_source(key) for key in sources]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def start(self):
        """Start the orchestrator"""
        if self.running:
            logger.warning("Orchestrator already running")
            return
        
        logger.info("Starting Data Orchestrator...")
        self.setup_schedule()
        self.scheduler.start()
        self.running = True
        logger.info("✓ Data Orchestrator started successfully")
    
    def stop(self):
        """Stop the orchestrator"""
        if not self.running:
            return
        
        logger.info("Stopping Data Orchestrator...")
        self.scheduler.shutdown()
        self.running = False
        logger.info("✓ Data Orchestrator stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            **self.stats,
            "running": self.running,
            "enabled_sources": sum(1 for s in self.sources.values() if s.enabled),
            "total_sources": len(self.sources),
            "next_updates": [
                {
                    "job_id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ] if self.running else []
        }
    
    def enable_source(self, source_key: str):
        """Enable a data source"""
        if source_key in self.sources:
            self.sources[source_key].enabled = True
            logger.info(f"Enabled source: {source_key}")
    
    def disable_source(self, source_key: str):
        """Disable a data source"""
        if source_key in self.sources:
            self.sources[source_key].enabled = False
            logger.info(f"Disabled source: {source_key}")


