#!/usr/bin/env python3
"""
SDFAI Storage Module - Abstract Storage Interface
Provides unified storage abstraction for different backends.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class StorageItem:
    key: str
    value: str
    metadata: Dict = None
    created_at: float = None
    updated_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class BaseStore(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[StorageItem]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, metadata: Dict = None) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list(self, prefix: str = None, limit: int = 100) -> List[StorageItem]:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass


class BaseVectorStore(ABC):
    """Abstract base class for vector storage backends."""
    
    @abstractmethod
    def add(self, doc_id: str, text: str, metadata: Dict = None) -> bool:
        pass
    
    @abstractmethod
    def search(self, query: str, n_results: int = 5, 
               filter: Dict = None) -> List[Dict]:
        pass
    
    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        pass
    
    @abstractmethod
    def count(self) -> int:
        pass


class BaseKVStore(ABC):
    """Abstract base class for key-value storage."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass
