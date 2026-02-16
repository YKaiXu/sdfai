#!/usr/bin/env python3
"""
SDFAI SQLite Storage Backend
Provides structured storage with indexing and full-text search.
"""
import os
import sqlite3
import json
import time
import threading
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base import BaseStore, StorageItem

logger = logging.getLogger(__name__)


class SQLiteStore(BaseStore):
    """
    SQLite-based storage backend.
    Supports:
    - CRUD operations
    - Indexing
    - Full-text search (FTS)
    - Transactions
    """
    
    def __init__(self, db_path: str = None, table: str = "storage"):
        if db_path is None:
            db_path = os.path.expanduser("~/.sdfai/data/storage.db")
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.table = table
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    metadata TEXT DEFAULT '{{}}',
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table}_created 
                ON {self.table}(created_at)
            """)
            
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self.table}_fts 
                USING fts5(key, value, content={self.table})
            """)
            
            conn.commit()
    
    def get(self, key: str) -> Optional[StorageItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    f"SELECT * FROM {self.table} WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if row:
                    return StorageItem(
                        key=row['key'],
                        value=row['value'],
                        metadata=json.loads(row['metadata']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                return None
        except Exception as e:
            logger.error(f"SQLite get failed: {e}")
            return None
    
    def set(self, key: str, value: str, metadata: Dict = None) -> bool:
        with self._lock:
            try:
                now = time.time()
                metadata_json = json.dumps(metadata or {})
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"""
                        INSERT INTO {self.table} (key, value, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            value = excluded.value,
                            metadata = excluded.metadata,
                            updated_at = excluded.updated_at
                    """, (key, value, metadata_json, now, now))
                    
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"SQLite set failed: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"DELETE FROM {self.table} WHERE key = ?", (key,))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"SQLite delete failed: {e}")
                return False
    
    def list(self, prefix: str = None, limit: int = 100) -> List[StorageItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if prefix:
                    cursor = conn.execute(
                        f"SELECT * FROM {self.table} WHERE key LIKE ? ORDER BY created_at DESC LIMIT ?",
                        (f"{prefix}%", limit)
                    )
                else:
                    cursor = conn.execute(
                        f"SELECT * FROM {self.table} ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    )
                
                items = []
                for row in cursor.fetchall():
                    items.append(StorageItem(
                        key=row['key'],
                        value=row['value'],
                        metadata=json.loads(row['metadata']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
                
                return items
        except Exception as e:
            logger.error(f"SQLite list failed: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    f"SELECT 1 FROM {self.table} WHERE key = ?",
                    (key,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"SQLite exists failed: {e}")
            return False
    
    def clear(self) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"DELETE FROM {self.table}")
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"SQLite clear failed: {e}")
                return False
    
    def search(self, query: str, limit: int = 10) -> List[StorageItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(f"""
                    SELECT s.* FROM {self.table} s
                    JOIN {self.table}_fts fts ON s.key = fts.key
                    WHERE {self.table}_fts MATCH ?
                    ORDER BY fts.rank
                    LIMIT ?
                """, (query, limit))
                
                items = []
                for row in cursor.fetchall():
                    items.append(StorageItem(
                        key=row['key'],
                        value=row['value'],
                        metadata=json.loads(row['metadata']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
                
                return items
        except Exception as e:
            logger.error(f"SQLite search failed: {e}")
            return []
    
    def batch_set(self, items: Dict[str, str]) -> bool:
        with self._lock:
            try:
                now = time.time()
                with sqlite3.connect(self.db_path) as conn:
                    for key, value in items.items():
                        conn.execute(f"""
                            INSERT INTO {self.table} (key, value, metadata, created_at, updated_at)
                            VALUES (?, ?, '{{}}', ?, ?)
                            ON CONFLICT(key) DO UPDATE SET
                                value = excluded.value,
                                updated_at = excluded.updated_at
                        """, (key, value, now, now))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"SQLite batch_set failed: {e}")
                return False
    
    def count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {self.table}")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"SQLite count failed: {e}")
            return 0


class MemoryStore(SQLiteStore):
    """
    Specialized SQLite store for memory entries.
    Adds user/platform context and expiration support.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.sdfai/data/memory.db")
        super().__init__(db_path, table="memory")
        self._init_memory_table()
    
    def _init_memory_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    category TEXT DEFAULT 'general',
                    importance INTEGER DEFAULT 0,
                    embedding_id TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now')),
                    expires_at REAL,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(user_id, platform, key)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_user 
                ON memory(user_id, platform)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_category 
                ON memory(category)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_importance 
                ON memory(importance DESC)
            """)
            
            conn.commit()
    
    def remember(self, user_id: str, platform: str, key: str, value: str,
                 category: str = "general", importance: int = 0,
                 summary: str = "", expires_in: float = None,
                 metadata: Dict = None, embedding_id: str = None) -> bool:
        with self._lock:
            try:
                now = time.time()
                expires_at = now + expires_in if expires_in else None
                metadata_json = json.dumps(metadata or {})
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO memory 
                        (user_id, platform, key, value, summary, category,
                         importance, embedding_id, created_at, updated_at,
                         expires_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, platform, key) DO UPDATE SET
                            value = excluded.value,
                            summary = excluded.summary,
                            category = excluded.category,
                            importance = excluded.importance,
                            embedding_id = excluded.embedding_id,
                            updated_at = excluded.updated_at,
                            expires_at = excluded.expires_at,
                            metadata = excluded.metadata
                    """, (user_id, platform, key, value, summary, category,
                          importance, embedding_id, now, now, expires_at, metadata_json))
                    
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Remember failed: {e}")
                return False
    
    def recall(self, user_id: str, platform: str, key: str = None,
               category: str = None, limit: int = 10) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT * FROM memory 
                    WHERE user_id = ? AND platform = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                """
                params = [user_id, platform, time.time()]
                
                if key:
                    query += " AND key = ?"
                    params.append(key)
                
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                query += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Recall failed: {e}")
            return []
    
    def forget(self, user_id: str, platform: str, key: str = None) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    if key:
                        conn.execute(
                            "DELETE FROM memory WHERE user_id = ? AND platform = ? AND key = ?",
                            (user_id, platform, key)
                        )
                    else:
                        conn.execute(
                            "DELETE FROM memory WHERE user_id = ? AND platform = ?",
                            (user_id, platform)
                        )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Forget failed: {e}")
                return False
    
    def get_summaries(self, user_id: str, platform: str, limit: int = 20) -> List[Dict]:
        entries = self.recall(user_id, platform, limit=limit)
        return [
            {
                "key": e['key'],
                "summary": e['summary'] or e['value'][:100],
                "category": e['category'],
                "importance": e['importance']
            }
            for e in entries
        ]
    
    def cleanup_expired(self) -> int:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM memory WHERE expires_at IS NOT NULL AND expires_at < ?",
                        (time.time(),)
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
                return 0


class SessionStore(SQLiteStore):
    """
    Specialized SQLite store for user sessions.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.sdfai/data/sessions.db")
        super().__init__(db_path, table="sessions")
        self._init_session_table()
    
    def _init_session_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    chat_id TEXT,
                    language TEXT DEFAULT 'zh-CN',
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    preferences TEXT DEFAULT '{}',
                    context TEXT DEFAULT '{}',
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now')),
                    last_active REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user 
                ON sessions(user_id, platform)
            """)
            
            conn.commit()
    
    def save_session(self, session_id: str, user_id: str, platform: str,
                     chat_id: str = None, language: str = "zh-CN",
                     timezone: str = "Asia/Shanghai", preferences: Dict = None,
                     context: Dict = None) -> bool:
        with self._lock:
            try:
                now = time.time()
                preferences_json = json.dumps(preferences or {})
                context_json = json.dumps(context or {})
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO sessions 
                        (session_id, user_id, platform, chat_id, language, timezone,
                         preferences, context, created_at, updated_at, last_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(session_id) DO UPDATE SET
                            language = excluded.language,
                            timezone = excluded.timezone,
                            preferences = excluded.preferences,
                            context = excluded.context,
                            updated_at = excluded.updated_at,
                            last_active = excluded.last_active
                    """, (session_id, user_id, platform, chat_id, language,
                          timezone, preferences_json, context_json, now, now, now))
                    
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Save session failed: {e}")
                return False
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Load session failed: {e}")
            return None
    
    def update_activity(self, session_id: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                        (time.time(), session_id)
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Update activity failed: {e}")
                return False
