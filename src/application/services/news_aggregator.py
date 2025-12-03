"""
Advanced News & Data Aggregation Service for Multi-Agent Trading System
Fetches real-time financial, crypto, and forex news from multiple sources
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
import re
from dataclasses import dataclass, asdict
import hashlib
from functools import wraps
import time
from src.utilities.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Article:
    """Structured article data"""
    title: str
    content: str
    url: str
    source: str
    published_at: str
    category: str
    tags: List[str]
    summary: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_hash(self) -> str:
        """Generate unique hash for deduplication"""
        content = f"{self.title}{self.url}{self.source}"
        return hashlib.md5(content.encode()).hexdigest()


def retry_on_failure(max_retries: int = 3, delay: float = 2.0):
    """Decorator for retrying failed requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator


class NewsAggregator:
    """Advanced news aggregation system with multiple source support"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_hashes = set()
        
        # Headers to mimic real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # Source configurations
        self.sources = {
            'reuters': {
                'base_url': 'https://www.reuters.com',
                'pages': [
                    '/markets/currencies/',
                    '/markets/stocks/us/',
                    '/markets/global-market-data/'
                ],
                'parser': self._parse_reuters
            },
            'bloomberg': {
                'base_url': 'https://www.bloomberg.com',
                'pages': [
                    '/africa',
                    '/markets/currencies',
                    '/markets/rates-bonds'
                ],
                'parser': self._parse_bloomberg
            },
            'coindesk': {
                'base_url': 'https://www.coindesk.com',
                'pages': [
                    '/markets',
                    '/tag/bitcoin',
                    '/tag/ethereum',
                    '/tag/xrp',
                    '/tag/solana'
                ],
                'parser': self._parse_coindesk
            },
            'financefeeds': {
                'base_url': 'https://financefeeds.com',
                'pages': ['/category/market-news/'],
                'parser': self._parse_financefeeds
            },
            'fxcoinz': {
                'base_url': 'https://www.fxcoinz.com',
                'pages': [
                    '/news/crypto-news',
                    '/news/forex-news',
                    '/forecasts/crypto-forecasts',
                    '/forecasts/forex-forecasts'
                ],
                'parser': self._parse_fxcoinz
            },
            'cryptofaxreport': {
                'base_url': 'https://www.cryptofaxreport.com',
                'pages': ['/explore'],
                'parser': self._parse_generic
            },
            'newsnow_crypto': {
                'base_url': 'https://www.newsnow.com',
                'pages': ['/us/Business/Cryptocurrencies'],
                'parser': self._parse_newsnow
            }
        }
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=self.max_concurrent, ssl=False)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @retry_on_failure(max_retries=3)
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content with error handling"""
        try:
            async with self.session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep essential punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\'\"\(\)\$\%\€\£\¥]', '', text)
        return text.strip()
    
    def _extract_publish_date(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract publication date from common selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get('datetime') or element.get_text()
                try:
                    # Try to parse various date formats
                    return date_text.strip()
                except:
                    continue
        return datetime.now().isoformat()
    
    async def _parse_reuters(self, url: str, html: str) -> List[Article]:
        """Parse Reuters articles"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find article cards/items
        article_elements = soup.select('article, .story-card, [data-testid*="article"]')
        
        for element in article_elements[:20]:  # Limit per page
            try:
                # Extract title
                title_elem = element.select_one('h2, h3, .heading, [data-testid*="heading"]')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                # Extract link
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                # Extract summary/content
                summary_elem = element.select_one('p, .summary, .description')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                # Extract date
                published_at = self._extract_publish_date(
                    element,
                    ['time[datetime]', '[datetime]', '.timestamp', '.date']
                )
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='Reuters',
                    published_at=published_at,
                    category='forex' if 'currencies' in url else 'stocks',
                    tags=['forex', 'markets', 'reuters']
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing Reuters article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_bloomberg(self, url: str, html: str) -> List[Article]:
        """Parse Bloomberg articles"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Bloomberg uses various article containers
        article_elements = soup.select('article, .story-package-module__story, [data-component="card"]')
        
        for element in article_elements[:20]:
            try:
                title_elem = element.select_one('h3, h2, .headline, [class*="headline"]')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                summary_elem = element.select_one('p, .summary')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['time', '[datetime]', '.timestamp']
                )
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='Bloomberg',
                    published_at=published_at,
                    category='forex' if 'currencies' in url else 'markets',
                    tags=['bloomberg', 'markets', 'forex']
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing Bloomberg article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_coindesk(self, url: str, html: str) -> List[Article]:
        """Parse CoinDesk articles"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # CoinDesk article containers
        article_elements = soup.select('article, .card, .article-card, [class*="articleCard"]')
        
        for element in article_elements[:20]:
            try:
                title_elem = element.select_one('h2, h3, h4, .headline, [class*="headline"]')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                summary_elem = element.select_one('p, .description, .excerpt')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['time', '[datetime]', '.timestamp', '.published-date']
                )
                
                # Extract tags from URL
                tags = ['coindesk', 'crypto']
                if 'bitcoin' in url.lower():
                    tags.append('bitcoin')
                elif 'ethereum' in url.lower():
                    tags.append('ethereum')
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='CoinDesk',
                    published_at=published_at,
                    category='crypto',
                    tags=tags
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing CoinDesk article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_financefeeds(self, url: str, html: str) -> List[Article]:
        """Parse FinanceFeeds articles"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        article_elements = soup.select('article, .post, .entry, [class*="article"]')
        
        for element in article_elements[:20]:
            try:
                title_elem = element.select_one('h2, h3, .entry-title, .post-title')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                summary_elem = element.select_one('p, .excerpt, .summary')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['time', '.published', '.date']
                )
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='FinanceFeeds',
                    published_at=published_at,
                    category='markets',
                    tags=['financefeeds', 'forex', 'markets']
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing FinanceFeeds article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_fxcoinz(self, url: str, html: str) -> List[Article]:
        """Parse FXCoinz articles"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        article_elements = soup.select('article, .news-item, .post, [class*="article"]')
        
        for element in article_elements[:20]:
            try:
                title_elem = element.select_one('h2, h3, h4, .title')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                summary_elem = element.select_one('p, .excerpt, .description')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['time', '.date', '.published']
                )
                
                category = 'crypto' if 'crypto' in url else 'forex'
                tags = ['fxcoinz', category]
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='FXCoinz',
                    published_at=published_at,
                    category=category,
                    tags=tags
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing FXCoinz article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_newsnow(self, url: str, html: str) -> List[Article]:
        """Parse NewsNow aggregator"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        article_elements = soup.select('.hl, .hentry, [class*="article"]')
        
        for element in article_elements[:20]:
            try:
                title_elem = element.select_one('a, .title')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                article_url = urljoin(url, title_elem['href']) if title_elem.get('href') else url
                
                summary_elem = element.select_one('.summary, .excerpt')
                content = self._clean_text(summary_elem.get_text()) if summary_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['.time', '.date', 'time']
                )
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source='NewsNow',
                    published_at=published_at,
                    category='crypto',
                    tags=['newsnow', 'crypto', 'aggregator']
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing NewsNow article: {str(e)}")
                continue
        
        return articles
    
    async def _parse_generic(self, url: str, html: str) -> List[Article]:
        """Generic parser for unknown sources"""
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try common article selectors
        article_elements = soup.select('article, .post, .entry, .card, [class*="article"]')
        
        for element in article_elements[:15]:
            try:
                # Try various title selectors
                title_elem = element.select_one('h1, h2, h3, h4, .title, .headline, [class*="title"]')
                if not title_elem:
                    continue
                title = self._clean_text(title_elem.get_text())
                
                if len(title) < 10:  # Skip if title too short
                    continue
                
                # Find link
                link_elem = element.select_one('a[href]')
                article_url = urljoin(url, link_elem['href']) if link_elem else url
                
                # Find content
                content_elem = element.select_one('p, .content, .excerpt, .summary, .description')
                content = self._clean_text(content_elem.get_text()) if content_elem else title
                
                published_at = self._extract_publish_date(
                    element,
                    ['time', '[datetime]', '.date', '.published', '.timestamp']
                )
                
                source_name = urlparse(url).netloc.replace('www.', '').split('.')[0].title()
                
                article = Article(
                    title=title,
                    content=content,
                    url=article_url,
                    source=source_name,
                    published_at=published_at,
                    category='markets',
                    tags=[source_name.lower(), 'markets']
                )
                
                if article.get_hash() not in self.seen_hashes:
                    self.seen_hashes.add(article.get_hash())
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error parsing generic article: {str(e)}")
                continue
        
        return articles
    
    async def fetch_from_source(self, source_name: str) -> List[Article]:
        """Fetch articles from a specific source"""
        if source_name not in self.sources:
            logger.warning(f"Unknown source: {source_name}")
            return []
        
        source_config = self.sources[source_name]
        all_articles = []
        
        for page in source_config['pages']:
            url = source_config['base_url'] + page
            
            try:
                logger.info(f"Fetching {url}")
                html = await self._fetch_page(url)
                
                if html:
                    articles = await source_config['parser'](url, html)
                    all_articles.extend(articles)
                    logger.info(f"Extracted {len(articles)} articles from {url}")
                    
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching from {url}: {str(e)}")
                continue
        
        return all_articles
    
    async def fetch_all_sources(self) -> Dict[str, List[Article]]:
        """Fetch articles from all configured sources concurrently"""
        logger.info("Starting comprehensive news aggregation...")
        
        tasks = [self.fetch_from_source(source) for source in self.sources.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        aggregated = {}
        total_articles = 0
        
        for source_name, result in zip(self.sources.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {source_name}: {str(result)}")
                aggregated[source_name] = []
            else:
                aggregated[source_name] = result
                total_articles += len(result)
                logger.info(f"✓ {source_name}: {len(result)} articles")
        
        logger.info(f"Total articles fetched: {total_articles}")
        return aggregated
    
    def prepare_for_rag(self, articles: List[Article]) -> List[Dict[str, Any]]:
        """Convert articles to RAG-compatible format"""
        documents = []
        
        for article in articles:
            # Combine title and content for better context
            full_text = f"{article.title}\n\n{article.content}"
            
            documents.append({
                "text": full_text,
                "metadata": {
                    "source": article.source,
                    "url": article.url,
                    "category": article.category,
                    "tags": ",".join(article.tags),
                    "published_at": article.published_at,
                    "timestamp": datetime.now().isoformat(),
                    "type": "news"
                }
            })
        
        return documents


class NewsRAGUpdater:
    """Orchestrates news fetching and RAG updates"""
    
    def __init__(self, rag_service):
        self.rag_service = rag_service
        self.aggregator = None
    
    async def update_all_news(self) -> Dict[str, Any]:
        """Fetch all news and update RAG service"""
        stats = {
            "start_time": datetime.now().isoformat(),
            "sources_processed": 0,
            "total_articles": 0,
            "documents_added": 0,
            "errors": []
        }
        
        try:
            async with NewsAggregator(max_concurrent=10) as aggregator:
                self.aggregator = aggregator
                
                # Fetch from all sources
                all_articles = await aggregator.fetch_all_sources()
                
                # Process each source
                for source_name, articles in all_articles.items():
                    if articles:
                        # Prepare documents for RAG
                        documents = aggregator.prepare_for_rag(articles)
                        
                        # Add to RAG service
                        success = await self.rag_service.add_documents(
                            documents,
                            "news_collection"  # or your collection name
                        )
                        
                        if success:
                            stats["sources_processed"] += 1
                            stats["total_articles"] += len(articles)
                            stats["documents_added"] += len(documents)
                        else:
                            stats["errors"].append(f"Failed to add {source_name} to RAG")
                
                stats["end_time"] = datetime.now().isoformat()
                logger.info(f"News update complete: {stats['documents_added']} documents added")
                
        except Exception as e:
            logger.error(f"Error updating news: {str(e)}")
            stats["errors"].append(str(e))
        
        return stats
    
    async def update_specific_categories(self, categories: List[str]) -> Dict[str, Any]:
        """Update only specific categories (crypto, forex, stocks)"""
        stats = {"categories": {}}
        
        async with NewsAggregator() as aggregator:
            all_articles = await aggregator.fetch_all_sources()
            
            # Filter by category
            for category in categories:
                filtered_articles = []
                for source_articles in all_articles.values():
                    filtered_articles.extend([
                        a for a in source_articles 
                        if a.category.lower() == category.lower()
                    ])
                
                if filtered_articles:
                    documents = aggregator.prepare_for_rag(filtered_articles)
                    success = await self.rag_service.add_documents(
                        documents,
                        f"{category}_news_collection"
                    )
                    
                    stats["categories"][category] = {
                        "articles": len(filtered_articles),
                        "success": success
                    }
        
        return stats


