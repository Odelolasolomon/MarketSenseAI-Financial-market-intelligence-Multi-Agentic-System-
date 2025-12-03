"""
RAG Service - Retrieval Augmented Generation with Comprehensive Data Integration
Integrates NewsAggregator, DeepScraper, DataOrchestrator, and DataCollector
"""
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import hashlib
import os
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from src.utilities.logger import get_logger
from src.config.settings import get_settings
from src.config.constants import (
    CHROMA_COLLECTION_MACRO,
    CHROMA_COLLECTION_CRYPTO,
    CHROMA_COLLECTION_NEWS
)

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RAGDocument:
    """Standardized document format for RAG"""
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    id: Optional[str] = None
    
    def generate_id(self) -> str:
        """Generate unique ID based on content and metadata"""
        content = f"{self.text}{json.dumps(self.metadata, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


class RAGService:
    """Robust RAG service that integrates all data collection components"""
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG service
        
        Args:
            embedding_model_name: Name of the sentence transformer model
        """
        self.embedding_model_name = embedding_model_name
        self.embedding_model = None
        self.client = None
        self.collections = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.initialized = False
        
        # Collection name mapping for backward compatibility
        self.collection_mapping = {
            # Agent collection names -> Actual collection names
            "crypto": CHROMA_COLLECTION_CRYPTO,
            "news": CHROMA_COLLECTION_NEWS,
            "macro": CHROMA_COLLECTION_MACRO,
            # Also map the actual names to themselves
            CHROMA_COLLECTION_CRYPTO: CHROMA_COLLECTION_CRYPTO,
            CHROMA_COLLECTION_NEWS: CHROMA_COLLECTION_NEWS,
            CHROMA_COLLECTION_MACRO: CHROMA_COLLECTION_MACRO
        }
    
    async def initialize(self):
        """Initialize the RAG service asynchronously"""
        if self.initialized:
            return
        
        try:
            logger.info("Initializing RAG Service...")
            
            # Disable ChromaDB telemetry to avoid errors
            os.environ['ANONYMIZED_TELEMETRY'] = 'False'
            
            # Import heavy dependencies only when needed
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            from sentence_transformers import SentenceTransformer
            
            # Initialize ChromaDB client with telemetry disabled
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model in thread pool
            self.embedding_model = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: SentenceTransformer(self.embedding_model_name)
            )
            
            # Initialize collections
            await self._initialize_collections()
            
            self.initialized = True
            logger.info("[OK] RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {str(e)}")
            raise
    
    async def _initialize_collections(self):
        """Initialize all collections with proper configuration"""
        collection_configs = {
            CHROMA_COLLECTION_MACRO: {
                "metadata": {"hnsw:space": "cosine", "description": "Macroeconomic data"},
                "embedding_function": None  # We'll handle embeddings manually
            },
            CHROMA_COLLECTION_CRYPTO: {
                "metadata": {"hnsw:space": "cosine", "description": "Cryptocurrency data"},
                "embedding_function": None
            },
            CHROMA_COLLECTION_NEWS: {
                "metadata": {"hnsw:space": "cosine", "description": "News articles"},
                "embedding_function": None
            }
        }
        
        for name, config in collection_configs.items():
            try:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata=config["metadata"],
                    embedding_function=config["embedding_function"]
                )
                logger.info(f"[OK] Collection '{name}' initialized")
            except Exception as e:
                logger.error(f"Failed to initialize collection '{name}': {str(e)}")
                # Create with default settings if failed
                self.collections[name] = self.client.create_collection(name=name)
    
    def _get_collection(self, collection_name: str):
        """
        Get collection by name with intelligent fallback and name mapping
        
        Args:
            collection_name: Collection name requested by agent (could be 'crypto', 'news', 'macro' 
                           or actual collection names like 'crypto_data', 'news_sentiment', 'macro_data')
        
        Returns:
            Collection object or None if not found
        """
        # First, check if it's a mapped name
        mapped_name = self.collection_mapping.get(collection_name)
        
        if mapped_name and mapped_name in self.collections:
            return self.collections[mapped_name]
        
        # If not found via mapping, try the name directly
        if collection_name in self.collections:
            return self.collections[collection_name]
        
        # Try common variations
        variations = [
            f"{collection_name}_data",
            f"{collection_name}_sentiment", 
            f"{collection_name}_collection",
            collection_name.replace("_data", ""),
            collection_name.replace("_sentiment", ""),
            collection_name.replace("_collection", "")
        ]
        
        for variation in variations:
            if variation in self.collections:
                logger.debug(f"Found collection '{variation}' for requested name '{collection_name}'")
                return self.collections[variation]
        
        logger.warning(f"Collection '{collection_name}' not found (tried mapping and variations)")
        return None
    
    async def add_documents(
        self,
        documents: List[Union[Dict[str, Any], RAGDocument]],
        collection_name: str,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Add documents to a collection with robust error handling
        
        Args:
            documents: List of documents (dict or RAGDocument)
            collection_name: Target collection name
            batch_size: Number of documents to process at once
            
        Returns:
            Statistics about the operation
        """
        if not self.initialized:
            await self.initialize()
        
        stats = {
            "total_documents": len(documents),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "collection": collection_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if not documents:
            logger.warning(f"No documents provided for collection '{collection_name}'")
            return stats
        
        collection = self._get_collection(collection_name)
        
        if not collection:
            stats["errors"].append(f"Collection '{collection_name}' not found")
            return stats
        
        try:
            # Convert dicts to RAGDocument objects
            rag_docs = []
            for doc in documents:
                try:
                    if isinstance(doc, dict):
                        rag_doc = RAGDocument(
                            text=doc.get("text", ""),
                            metadata=doc.get("metadata", {})
                        )
                    else:
                        rag_doc = doc
                    
                    # Generate ID if not provided
                    if not rag_doc.id:
                        rag_doc.id = rag_doc.generate_id()
                    
                    rag_docs.append(rag_doc)
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"Document conversion error: {str(e)}")
            
            # Process in batches
            for i in range(0, len(rag_docs), batch_size):
                batch = rag_docs[i:i + batch_size]
                
                try:
                    # Generate embeddings
                    texts = [doc.text for doc in batch]
                    embeddings = await self._generate_embeddings(texts)
                    
                    # Update documents with embeddings
                    for doc, embedding in zip(batch, embeddings):
                        doc.embedding = embedding
                    
                    # Prepare data for ChromaDB
                    ids = [doc.id for doc in batch]
                    documents_list = [doc.text for doc in batch]
                    metadatas = [doc.metadata for doc in batch]
                    embeddings_list = [doc.embedding for doc in batch]
                    
                    # Add to collection
                    collection.add(
                        ids=ids,
                        documents=documents_list,
                        metadatas=metadatas,
                        embeddings=embeddings_list
                    )
                    
                    stats["successful"] += len(batch)
                    logger.debug(f"Added batch of {len(batch)} documents to '{collection_name}'")
                    
                except Exception as e:
                    stats["failed"] += len(batch)
                    stats["errors"].append(f"Batch {i//batch_size} error: {str(e)}")
                    logger.error(f"Error processing batch: {str(e)}")
            
            logger.info(f"Added {stats['successful']}/{stats['total_documents']} documents to '{collection_name}'")
            
        except Exception as e:
            logger.error(f"Critical error adding documents: {str(e)}")
            stats["errors"].append(f"Critical error: {str(e)}")
        
        return stats
    
    async def query(
        self,
        query_text: str,
        collection_names: Union[str, List[str]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query documents from collection(s)
        
        Args:
            query_text: The query text
            collection_names: Single collection name or list of names
            n_results: Number of results per collection
            where: Filter by metadata
            where_document: Filter by document content
            
        Returns:
            Query results with metadata
        """
        if not self.initialized:
            await self.initialize()
        
        if collection_names is None:
            collection_names = list(self.collections.keys())
        elif isinstance(collection_names, str):
            collection_names = [collection_names]
        
        results = {
            "query": query_text,
            "total_results": 0,
            "collections": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate query embedding
        try:
            query_embedding = await self._generate_embeddings([query_text])
            query_embedding = query_embedding[0]
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            return results
        
        # Query each collection
        for collection_name in collection_names:
            collection = self._get_collection(collection_name)
            
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found, skipping")
                results["collections"][collection_name] = {
                    "count": 0,
                    "results": [],
                    "error": f"Collection '{collection_name}' not found"
                }
                continue
            
            try:
                collection_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=["documents", "metadatas", "distances"]
                )
                
                # Format results
                formatted_results = []
                if collection_results["documents"]:
                    for i in range(len(collection_results["documents"][0])):
                        formatted_results.append({
                            "document": collection_results["documents"][0][i],
                            "metadata": collection_results["metadatas"][0][i],
                            "distance": collection_results["distances"][0][i],
                            "score": 1 - collection_results["distances"][0][i]  # Convert distance to similarity
                        })
                
                results["collections"][collection_name] = {
                    "count": len(formatted_results),
                    "results": formatted_results
                }
                results["total_results"] += len(formatted_results)
                
            except Exception as e:
                logger.error(f"Error querying collection '{collection_name}': {str(e)}")
                results["collections"][collection_name] = {
                    "count": 0,
                    "results": [],
                    "error": str(e)
                }
        
        return results
    
    async def query_collection(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Backward compatibility method for querying a single collection
        Returns format that SynthesisAgent and other agents expect
        
        Args:
            query: Search query
            collection_name: Collection to search
            n_results: Number of results
            
        Returns:
            List of documents in old format: [{"text": "...", "metadata": {...}}]
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get the collection (with intelligent mapping)
            collection = self._get_collection(collection_name)
            
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found for query")
                return []
            
            # Use the new query method
            result = await self.query(
                query_text=query,
                collection_names=[collection_name],
                n_results=n_results
            )
            
            # Convert to old format that SynthesisAgent expects
            documents = []
            collection_results = result.get("collections", {}).get(collection_name, {})
            
            if collection_results.get("results"):
                for item in collection_results["results"]:
                    documents.append({
                        "text": item.get("document", ""),
                        "metadata": item.get("metadata", {}),
                        "distance": item.get("distance", 0),
                        "score": item.get("score", 0)
                    })
            
            logger.debug(f"Query collection '{collection_name}' returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error querying collection '{collection_name}': {str(e)}")
            return []
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with error handling"""
        if not texts:
            return []
        
        try:
            # Run embedding generation in thread pool
            embeddings = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.embedding_model.encode(texts, show_progress_bar=False)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            # Return zero vectors as fallback
            if self.embedding_model:
                dim = self.embedding_model.get_sentence_embedding_dimension()
                return [[0.0] * dim for _ in range(len(texts))]
            else:
                return [[0.0] * 384 for _ in range(len(texts))]  # Default dimension
    
    # ========== Integration with NewsAggregator ==========
    
    async def update_news(self, max_concurrent: int = 5) -> Dict[str, Any]:
        """
        Update news using NewsAggregator
        
        Args:
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Update statistics
        """
        # Import inside method to avoid circular dependency
        from src.application.services.news_aggregator import NewsAggregator
        
        stats = {
            "success": False,
            "articles_fetched": 0,
            "documents_added": 0,
            "sources_processed": 0,
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with NewsAggregator(max_concurrent=max_concurrent) as aggregator:
                # Fetch from all sources
                all_articles = await aggregator.fetch_all_sources()
                
                documents = []
                
                for source_name, articles in all_articles.items():
                    if articles:
                        source_docs = aggregator.prepare_for_rag(articles)
                        documents.extend(source_docs)
                        stats["sources_processed"] += 1
                        stats["articles_fetched"] += len(articles)
                        logger.info(f"[OK] {source_name}: {len(articles)} articles")
                
                # Add to news collection
                if documents:
                    result = await self.add_documents(documents, CHROMA_COLLECTION_NEWS)
                    stats["documents_added"] = result["successful"]
                    stats["success"] = result["successful"] > 0
                    
                    if result["errors"]:
                        stats["errors"].extend(result["errors"])
                
        except Exception as e:
            logger.error(f"Error updating news: {str(e)}")
            stats["errors"].append(str(e))
        
        return stats
    
    # ========== Integration with DeepScraper ==========
    
    async def scrape_dynamic_content(
        self,
        url: str,
        collection_name: str = CHROMA_COLLECTION_NEWS,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape dynamic content using DeepContentScraper
        
        Args:
            url: URL to scrape
            collection_name: Target collection
            headless: Whether to run browser in headless mode
            
        Returns:
            Scraping results
        """
        # Import inside method to avoid circular dependency
        from src.application.services.deep_scraper import DeepContentScraper
        
        stats = {
            "success": False,
            "url": url,
            "documents_added": 0,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with DeepContentScraper(headless=headless) as scraper:
                result = await scraper.scrape_dynamic_site(url, scroll_to_bottom=True)
                
                if result["success"]:
                    document = RAGDocument(
                        text=f"{result.get('title', '')}\n\n{result.get('text', '')}",
                        metadata={
                            "source": "DeepScraper",
                            "url": url,
                            "title": result.get('title', ''),
                            "type": "scraped_content",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    add_result = await self.add_documents([document], collection_name)
                    stats["success"] = add_result["successful"] > 0
                    stats["documents_added"] = add_result["successful"]
                    
                    if add_result["errors"]:
                        stats["error"] = "; ".join(add_result["errors"])
                
                else:
                    stats["error"] = result.get("error", "Unknown scraping error")
                    
        except Exception as e:
            logger.error(f"Error scraping dynamic content: {str(e)}")
            stats["error"] = str(e)
        
        return stats
    
    # ========== Integration with DataOrchestrator ==========
    
    async def update_from_data_orchestrator(self, source_key: str) -> Dict[str, Any]:
        """
        Update RAG from DataOrchestrator source
        
        Args:
            source_key: Key of the data source to update
            
        Returns:
            Update statistics
        """
        # Import inside method to avoid circular dependency
        from src.application.orchestrators.data_orchestrator import DataOrchestrator
        
        try:
            # Create orchestrator instance
            orchestrator = DataOrchestrator(self)
            
            # Update the specific source
            result = await orchestrator.update_source(source_key)
            
            return {
                "success": True,
                "source": source_key,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating from orchestrator: {str(e)}")
            return {
                "success": False,
                "source": source_key,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def update_all_via_orchestrator(self) -> Dict[str, Any]:
        """
        Update all sources via DataOrchestrator
        
        Returns:
            Update statistics
        """
        from src.application.orchestrators.data_orchestrator import DataOrchestrator
        
        try:
            orchestrator = DataOrchestrator(self)
            result = await orchestrator.update_all_sources()
            
            return {
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating via orchestrator: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # ========== Integration with DataCollector ==========
    # Note: DataCollector already imports RAGService, so we need to avoid circular import
    # We'll provide methods that DataCollector can call
    
    async def update_crypto_knowledge(self, crypto_data: Dict[str, Any]) -> bool:
        """
        Update crypto knowledge (called by DataCollector)
        
        Args:
            crypto_data: Crypto data from DataCollector
            
        Returns:
            Success status
        """
        try:
            if not crypto_data:
                return False
            
            document = RAGDocument(
                text=f"Crypto {crypto_data.get('symbol', 'Unknown')}: "
                     f"Price ${crypto_data.get('price', 0):,.2f}, "
                     f"24h Change {crypto_data.get('change_24h', 0):.2f}%, "
                     f"Volume {crypto_data.get('volume', 0):,.2f}",
                metadata={
                    "type": "crypto_price",
                    "symbol": crypto_data.get('symbol', ''),
                    "source": "Binance",
                    "timestamp": crypto_data.get('timestamp', datetime.now().isoformat())
                }
            )
            
            result = await self.add_documents([document], CHROMA_COLLECTION_CRYPTO)
            return result["successful"] > 0
            
        except Exception as e:
            logger.error(f"Error updating crypto knowledge: {str(e)}")
            return False
    
    async def update_macro_knowledge(self, economic_data: Dict[str, Any]) -> bool:
        """
        Update macro knowledge (called by DataCollector)
        
        Args:
            economic_data: Economic data from DataCollector
            
        Returns:
            Success status
        """
        try:
            if not economic_data:
                return False
            
            document = RAGDocument(
                text=f"Economic Indicators: {json.dumps(economic_data, indent=2)}",
                metadata={
                    "type": "economic_data",
                    "source": "FRED",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            result = await self.add_documents([document], CHROMA_COLLECTION_MACRO)
            return result["successful"] > 0
            
        except Exception as e:
            logger.error(f"Error updating macro knowledge: {str(e)}")
            return False
    
    async def update_news_knowledge(self, articles: List[Dict[str, Any]]) -> bool:
        """
        Update news knowledge (called by DataCollector)
        
        Args:
            articles: News articles from DataCollector
            
        Returns:
            Success status
        """
        try:
            if not articles:
                return False
            
            documents = []
            for article in articles:
                documents.append(RAGDocument(
                    text=f"{article.get('title', '')}\n\n{article.get('description', '')}",
                    metadata={
                        "type": "news",
                        "source": article.get('source', 'Unknown'),
                        "category": "business" if 'business' in str(article).lower() else "crypto",
                        "timestamp": datetime.now().isoformat()
                    }
                ))
            
            result = await self.add_documents(documents, CHROMA_COLLECTION_NEWS)
            return result["successful"] > 0
            
        except Exception as e:
            logger.error(f"Error updating news knowledge: {str(e)}")
            return False
    
    # ========== Utility Methods ==========
    
    async def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for collection(s)
        
        Args:
            collection_name: Optional specific collection name
            
        Returns:
            Collection statistics
        """
        if not self.initialized:
            await self.initialize()
        
        collections = [collection_name] if collection_name else self.collections.keys()
        
        stats = {
            "total_collections": len(self.collections),
            "collections": {},
            "timestamp": datetime.now().isoformat()
        }
        
        for name in collections:
            collection = self._get_collection(name)
            
            if not collection:
                stats["collections"][name] = {
                    "document_count": 0,
                    "exists": False,
                    "error": f"Collection '{name}' not found"
                }
                continue
            
            try:
                # Get count
                count = collection.count()
                
                stats["collections"][name] = {
                    "document_count": count,
                    "exists": True
                }
                
            except Exception as e:
                logger.error(f"Error getting stats for '{name}': {str(e)}")
                stats["collections"][name] = {
                    "document_count": 0,
                    "exists": False,
                    "error": str(e)
                }
        
        return stats
    
    async def clear_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        Clear all documents from a collection
        
        Args:
            collection_name: Collection to clear
            
        Returns:
            Clear operation result
        """
        if not self.initialized:
            await self.initialize()
        
        result = {
            "success": False,
            "collection": collection_name,
            "documents_cleared": 0,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            collection = self._get_collection(collection_name)
            
            if collection and collection.name in self.collections:
                # ChromaDB doesn't have a direct clear method, so we delete the collection
                self.client.delete_collection(collection.name)
                
                # Recreate the collection
                await self._initialize_collections()
                
                result["success"] = True
                result["documents_cleared"] = "all"
            else:
                result["error"] = f"Collection '{collection_name}' not found"
                
        except Exception as e:
            logger.error(f"Error clearing collection '{collection_name}': {str(e)}")
            result["error"] = str(e)
        
        return result
    
    async def close(self):
        """Clean up resources"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            self.initialized = False
            logger.info("RAG Service closed")
        except Exception as e:
            logger.error(f"Error closing RAG Service: {str(e)}")


# Async context manager support
class RAGServiceManager:
    """Context manager for RAG Service"""
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.service = RAGService(embedding_model_name)
    
    async def __aenter__(self):
        await self.service.initialize()
        return self.service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.service.close()


# Factory function for dependency injection
def get_rag_service():
    """Factory function to create RAG service for FastAPI dependency injection"""
    return RAGService()