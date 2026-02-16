#!/usr/bin/env python3
"""
SDFAI File Storage Backend
Provides Markdown-based storage for human-readable memory (OpenClaw style).
"""
import os
import threading
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from .base import BaseStore, StorageItem

logger = logging.getLogger(__name__)


class MarkdownStore(BaseStore):
    """
    Markdown-based storage backend.
    Provides human-readable memory files compatible with OpenClaw style.
    
    Directory Structure:
    memory/
    ├── MEMORY.md        # Core memory (long-term facts)
    └── YYYY-MM-DD.md    # Daily logs
    """
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/.sdfai/memory")
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.base_dir / "MEMORY.md"
        self._lock = threading.Lock()
        
        self._init_memory_file()
    
    def _init_memory_file(self):
        if not self.memory_file.exists():
            self._write_memory_file({
                "title": "SDFAI Core Memory",
                "created": datetime.now().isoformat(),
                "sections": {}
            })
    
    def _read_memory_file(self) -> Dict:
        try:
            if not self.memory_file.exists():
                return {"title": "SDFAI Core Memory", "sections": {}}
            
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._parse_markdown(content)
        except Exception as e:
            logger.error(f"Failed to read memory file: {e}")
            return {"title": "SDFAI Core Memory", "sections": {}}
    
    def _parse_markdown(self, content: str) -> Dict:
        result = {
            "title": "SDFAI Core Memory",
            "sections": {}
        }
        
        lines = content.split('\n')
        current_section = None
        current_key = None
        current_value = []
        
        for line in lines:
            if line.startswith('## '):
                if current_key and current_section:
                    if current_section not in result["sections"]:
                        result["sections"][current_section] = {}
                    result["sections"][current_section][current_key] = '\n'.join(current_value).strip()
                
                current_section = line[3:].strip()
                current_key = None
                current_value = []
            
            elif line.startswith('### '):
                if current_key and current_section:
                    if current_section not in result["sections"]:
                        result["sections"][current_section] = {}
                    result["sections"][current_section][current_key] = '\n'.join(current_value).strip()
                
                current_key = line[4:].strip()
                current_value = []
            
            elif current_key:
                current_value.append(line)
        
        if current_key and current_section:
            if current_section not in result["sections"]:
                result["sections"][current_section] = {}
            result["sections"][current_section][current_key] = '\n'.join(current_value).strip()
        
        return result
    
    def _write_memory_file(self, data: Dict):
        lines = [
            f"# {data.get('title', 'SDFAI Core Memory')}",
            "",
            f"Generated: {datetime.now().isoformat()}",
            ""
        ]
        
        for section, entries in data.get("sections", {}).items():
            lines.append(f"## {section}")
            lines.append("")
            
            for key, value in entries.items():
                lines.append(f"### {key}")
                lines.append("")
                lines.append(str(value))
                lines.append("")
        
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def get(self, key: str) -> Optional[StorageItem]:
        data = self._read_memory_file()
        
        for section, entries in data.get("sections", {}).items():
            if key in entries:
                return StorageItem(
                    key=key,
                    value=entries[key],
                    metadata={"section": section}
                )
        
        return None
    
    def set(self, key: str, value: str, metadata: Dict = None) -> bool:
        with self._lock:
            try:
                data = self._read_memory_file()
                
                section = metadata.get("section", "general") if metadata else "general"
                
                if "sections" not in data:
                    data["sections"] = {}
                
                if section not in data["sections"]:
                    data["sections"][section] = {}
                
                data["sections"][section][key] = value
                
                self._write_memory_file(data)
                return True
            except Exception as e:
                logger.error(f"Failed to set memory: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        with self._lock:
            try:
                data = self._read_memory_file()
                
                for section in data.get("sections", {}):
                    if key in data["sections"][section]:
                        del data["sections"][section][key]
                        self._write_memory_file(data)
                        return True
                
                return False
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
                return False
    
    def list(self, prefix: str = None, limit: int = 100) -> List[StorageItem]:
        data = self._read_memory_file()
        items = []
        
        for section, entries in data.get("sections", {}).items():
            for key, value in entries.items():
                if prefix is None or key.startswith(prefix):
                    items.append(StorageItem(
                        key=key,
                        value=value,
                        metadata={"section": section}
                    ))
                    
                    if len(items) >= limit:
                        return items
        
        return items
    
    def exists(self, key: str) -> bool:
        return self.get(key) is not None
    
    def clear(self) -> bool:
        with self._lock:
            try:
                self._write_memory_file({
                    "title": "SDFAI Core Memory",
                    "sections": {}
                })
                return True
            except Exception as e:
                logger.error(f"Failed to clear memory: {e}")
                return False


class DailyLogStore:
    """
    Daily log storage in Markdown format.
    Creates one file per day for conversation logs.
    """
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/.sdfai/memory")
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def _get_daily_file(self, date: datetime = None) -> Path:
        if date is None:
            date = datetime.now()
        
        return self.base_dir / f"{date.strftime('%Y-%m-%d')}.md"
    
    def append_log(self, content: str, date: datetime = None,
                   metadata: Dict = None) -> bool:
        with self._lock:
            try:
                log_file = self._get_daily_file(date)
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                entry_lines = [
                    f"### [{timestamp}]",
                    ""
                ]
                
                if metadata:
                    for key, value in metadata.items():
                        entry_lines.append(f"- {key}: {value}")
                    entry_lines.append("")
                
                entry_lines.append(content)
                entry_lines.append("")
                entry_lines.append("---")
                entry_lines.append("")
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write('\n'.join(entry_lines))
                
                return True
            except Exception as e:
                logger.error(f"Failed to append log: {e}")
                return False
    
    def read_log(self, date: datetime = None) -> str:
        try:
            log_file = self._get_daily_file(date)
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.read()
            
            return ""
        except Exception as e:
            logger.error(f"Failed to read log: {e}")
            return ""
    
    def list_logs(self, limit: int = 30) -> List[str]:
        try:
            log_files = sorted(
                self.base_dir.glob("????-??-??.md"),
                key=lambda p: p.name,
                reverse=True
            )
            
            return [f.stem for f in log_files[:limit]]
        except Exception as e:
            logger.error(f"Failed to list logs: {e}")
            return []
    
    def create_daily_header(self, date: datetime = None) -> bool:
        with self._lock:
            try:
                log_file = self._get_daily_file(date)
                
                if not log_file.exists():
                    if date is None:
                        date = datetime.now()
                    
                    header = [
                        f"# Daily Log - {date.strftime('%Y-%m-%d')}",
                        "",
                        f"Date: {date.strftime('%A, %B %d, %Y')}",
                        "",
                        "---",
                        ""
                    ]
                    
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(header))
                
                return True
            except Exception as e:
                logger.error(f"Failed to create daily header: {e}")
                return False


def create_file_stores(base_dir: str = None) -> Dict[str, Any]:
    """Factory function to create file-based stores."""
    return {
        "memory": MarkdownStore(base_dir),
        "daily_log": DailyLogStore(base_dir)
    }
