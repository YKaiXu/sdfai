#!/usr/bin/env python3
"""
SDFAI ChromaDB Vector Storage Backend
Provides semantic search capabilities for memory retrieval.
"""
import os
import threading
import logging
from typing import Optional, List, Dict, Any

from .base import BaseVectorStore

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not installed. Run: pip install chromadb")


class ChromaStore(BaseVectorStore):
    """
    ChromaDB-based vector storage backend.
    Enables semantic search for memory retrieval.
    """
    
    def __init__(self, persist_dir: str = None, collection: str = "sdfai"):
        if not CHROMA_AVAILABLE:
            raise RuntimeError("ChromaDB not installed. Run: pip install chromadb")
        
        if persist_dir is None:
            persist_dir = os.path.expanduser("~/.sdfai/data/chroma")
        
        os.makedirs(persist_dir, exist_ok=True)
        
        self.persist_dir = persist_dir
        self.collection_name = collection
        self._lock = threading.Lock()
        
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection,
            metadata={"description": f"SDFAI {collection} vectors"}
        )
        
        logger.info(f"ChromaDB initialized: {persist_dir}")
    
    def add(self, doc_id: str, text: str, metadata: Dict = None) -> bool:
        with self._lock:
            try:
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata or {}]
                )
                return True
            except Exception as e:
                logger.error(f"ChromaDB add failed: {e}")
                return False
    
    def add_batch(self, doc_ids: List[str], texts: List[str],
                  metadatas: List[Dict] = None) -> bool:
        with self._lock:
            try:
                self.collection.upsert(
                    ids=doc_ids,
                    documents=texts,
                    metadatas=metadatas or [{}] * len(doc_ids)
                )
                return True
            except Exception as e:
                logger.error(f"ChromaDB batch add failed: {e}")
                return False
    
    def search(self, query: str, n_results: int = 5,
               filter: Dict = None) -> List[Dict]:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )
            
            entries = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    entry = {
                        "id": doc_id,
                        "text": results['documents'][0][i] if results.get('documents') else "",
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                    }
                    if results.get('distances'):
                        entry["distance"] = results['distances'][0][i]
                    entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    def delete(self, doc_id: str) -> bool:
        with self._lock:
            try:
                self.collection.delete(ids=[doc_id])
                return True
            except Exception as e:
                logger.error(f"ChromaDB delete failed: {e}")
                return False
    
    def delete_batch(self, doc_ids: List[str]) -> bool:
        with self._lock:
            try:
                self.collection.delete(ids=doc_ids)
                return True
            except Exception as e:
                logger.error(f"ChromaDB batch delete failed: {e}")
                return False
    
    def delete_by_metadata(self, filter: Dict) -> bool:
        with self._lock:
            try:
                self.collection.delete(where=filter)
                return True
            except Exception as e:
                logger.error(f"ChromaDB delete by metadata failed: {e}")
                return False
    
    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"ChromaDB count failed: {e}")
            return 0
    
    def get(self, doc_id: str) -> Optional[Dict]:
        try:
            results = self.collection.get(ids=[doc_id])
            
            if results['ids']:
                return {
                    "id": results['ids'][0],
                    "text": results['documents'][0] if results.get('documents') else "",
                    "metadata": results['metadatas'][0] if results.get('metadatas') else {}
                }
            return None
        except Exception as e:
            logger.error(f"ChromaDB get failed: {e}")
            return None
    
    def clear(self) -> bool:
        with self._lock:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": f"SDFAI {self.collection_name} vectors"}
                )
                return True
            except Exception as e:
                logger.error(f"ChromaDB clear failed: {e}")
                return False


class MemoryVectorStore(ChromaStore):
    """
    Specialized vector store for memory entries.
    Adds user/platform context support.
    """
    
    def __init__(self, persist_dir: str = None):
        super().__init__(persist_dir, collection="memory")
    
    def index_memory(self, user_id: str, platform: str, key: str,
                     value: str, category: str = "general",
                     importance: int = 0) -> bool:
        import hashlib
        doc_id = hashlib.md5(f"{user_id}:{platform}:{key}".encode()).hexdigest()
        
        return self.add(
            doc_id=doc_id,
            text=f"{key}: {value}",
            metadata={
                "user_id": user_id,
                "platform": platform,
                "category": category,
                "importance": importance
            }
        )
    
    def search_user_memory(self, query: str, user_id: str,
                           platform: str = None, limit: int = 5) -> List[Dict]:
        filter_dict = {"user_id": user_id}
        if platform:
            filter_dict["platform"] = platform
        
        return self.search(query, n_results=limit, filter=filter_dict)
    
    def delete_user_memory(self, user_id: str, platform: str = None) -> bool:
        filter_dict = {"user_id": user_id}
        if platform:
            filter_dict["platform"] = platform
        
        return self.delete_by_metadata(filter_dict)


def create_vector_store(persist_dir: str = None) -> Optional[BaseVectorStore]:
    """Factory function to create vector store."""
    if not CHROMA_AVAILABLE:
        logger.warning("ChromaDB not available, vector search disabled")
        return None
    
    try:
        return MemoryVectorStore(persist_dir)
    except Exception as e:
        logger.error(f"Failed to create vector store: {e}")
        return None
