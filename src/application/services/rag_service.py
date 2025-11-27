"""
RAG Service - Retrieval Augmented Generation
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from src.config.settings import get_settings
from sentence_transformers import SentenceTransformer
import asyncio
from datetime import datetime
from src.config.constants import (
    CHROMA_COLLECTION_MACRO,
    CHROMA_COLLECTION_CRYPTO,
    CHROMA_COLLECTION_NEWS
)
from src.utilities.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RAGService:
    """Service for RAG operations with ChromaDB"""
    
    def __init__(self):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=settings.chroma_persist_directory
        ))
        
        # Initialize collections
        self.macro_collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_MACRO
        )
        self.crypto_collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_CRYPTO
        )
        self.news_collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NEWS
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str
    ) -> bool:
        """
        Add documents to a collection
        
        Args:
            documents: List of documents with text and metadata
            collection_name: Target collection
            
        Returns:
            Success status
        """
        try:
            collection = self._get_collection(collection_name)
            
            texts = [doc["text"] for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            ids = [f"{collection_name}_{i}_{datetime.now().timestamp()}" 
                   for i in range(len(documents))]
            
            # Generate embeddings
            embeddings = await self._generate_embeddings(texts)
            
            # Add to collection
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
    
    async def query_collection(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query a collection for relevant documents
        
        Args:
            query: Search query
            collection_name: Collection to search
            n_results: Number of results
            
        Returns:
            List of relevant documents
        """
        try:
            collection = self._get_collection(collection_name)
            
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            
            # Search
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )
            
            # Format results
            documents = []
            if results["documents"]:
                for i in range(len(results["documents"][0])):
                    documents.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error querying collection: {str(e)}")
            return []
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers"""
        try:
            embeddings = await asyncio.to_thread(
                self.embedding_model.encode, texts, show_progress_bar=False
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def _get_collection(self, collection_name: str):
        """Get collection by name"""
        collections = {
            CHROMA_COLLECTION_MACRO: self.macro_collection,
            CHROMA_COLLECTION_CRYPTO: self.crypto_collection,
            CHROMA_COLLECTION_NEWS: self.news_collection
        }
        return collections.get(collection_name, self.news_collection)
    
    async def update_macro_knowledge(self, economic_data: Dict[str, Any]):
        """Update macroeconomic knowledge base"""
        documents = [{
            "text": f"Economic Update: {datetime.now()}\n" + 
                   "\n".join([f"{k}: {v}" for k, v in economic_data.items()]),
            "metadata": {
                "type": "macro_data",
                "timestamp": datetime.now().isoformat()
            }
        }]
        await self.add_documents(documents, CHROMA_COLLECTION_MACRO)
    
    async def update_crypto_knowledge(self, crypto_data: Dict[str, Any]):
        """Update cryptocurrency knowledge base"""
        documents = [{
            "text": f"Crypto Update: {crypto_data.get('symbol', 'Unknown')}\n" +
                   f"Price: {crypto_data.get('price')}\n" +
                   f"24h Change: {crypto_data.get('change_24h')}%",
            "metadata": {
                "type": "crypto_data",
                "symbol": crypto_data.get("symbol"),
                "timestamp": datetime.now().isoformat()
            }
        }]
        await self.add_documents(documents, CHROMA_COLLECTION_CRYPTO)
    
    async def update_news_knowledge(self, articles: List[Dict[str, Any]]):
        """Update news knowledge base"""
        documents = []
        for article in articles:
            documents.append({
                "text": f"{article.get('title', '')}\n{article.get('description', '')}",
                "metadata": {
                    "type": "news",
                    "source": article.get("source", {}).get("name", ""),
                    "timestamp": article.get("publishedAt", datetime.now().isoformat())
                }
            })
        
        if documents:
            await self.add_documents(documents, CHROMA_COLLECTION_NEWS)