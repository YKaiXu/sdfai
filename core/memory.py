"""
SDFAI Memory Manager - 记忆管理器
三层存储：SQLite + ChromaDB + Markdown
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Memory:
    id: str
    content: str
    memory_type: str
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            importance=data.get("importance", 0.5),
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            access_count=data.get("access_count", 0),
            metadata=data.get("metadata", {})
        )


class MemoryManager:
    MEMORY_TYPES = [
        "conversation",
        "fact",
        "preference",
        "skill",
        "context",
        "temporary"
    ]
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memories: Dict[str, Memory] = {}
        self._load_memories()
    
    def _get_memory_file(self) -> Path:
        return self.data_dir / "memories.json"
    
    def _get_markdown_file(self) -> Path:
        return self.data_dir / "MEMORY.md"
    
    def _load_memories(self):
        memory_file = self._get_memory_file()
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text(encoding='utf-8'))
                for mem_data in data.get("memories", []):
                    mem = Memory.from_dict(mem_data)
                    self.memories[mem.id] = mem
            except:
                pass
    
    def _save_memories(self):
        memory_file = self._get_memory_file()
        data = {
            "updated_at": datetime.now().isoformat(),
            "memories": [m.to_dict() for m in self.memories.values()]
        }
        memory_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        self._save_markdown()
    
    def _save_markdown(self):
        md_file = self._get_markdown_file()
        md_content = "# SDFAI Memory\n\n"
        md_content += f"Last updated: {datetime.now().isoformat()}\n\n"
        
        for mem_type in self.MEMORY_TYPES:
            type_memories = [m for m in self.memories.values() if m.memory_type == mem_type]
            if type_memories:
                md_content += f"## {mem_type.title()}\n\n"
                for mem in sorted(type_memories, key=lambda m: m.importance, reverse=True):
                    md_content += f"### {mem.id}\n"
                    md_content += f"- Importance: {mem.importance}\n"
                    md_content += f"- Created: {mem.created_at.isoformat()}\n"
                    md_content += f"- Access count: {mem.access_count}\n"
                    md_content += f"\n{mem.content}\n\n"
        
        md_file.write_text(md_content, encoding='utf-8')
    
    def add_memory(
        self, 
        content: str, 
        memory_type: str = "conversation",
        importance: float = 0.5,
        metadata: Dict = None
    ) -> Memory:
        mem_id = f"{memory_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memories)}"
        
        memory = Memory(
            id=mem_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        self.memories[mem_id] = memory
        self._save_memories()
        return memory
    
    def get_memory(self, mem_id: str) -> Optional[Memory]:
        memory = self.memories.get(mem_id)
        if memory:
            memory.accessed_at = datetime.now()
            memory.access_count += 1
            self._save_memories()
        return memory
    
    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            if query_lower in memory.content.lower():
                results.append(memory)
        
        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:limit]
    
    def get_by_type(self, memory_type: str) -> List[Memory]:
        return [m for m in self.memories.values() if m.memory_type == memory_type]
    
    def get_important(self, threshold: float = 0.7) -> List[Memory]:
        return [m for m in self.memories.values() if m.importance >= threshold]
    
    def update_importance(self, mem_id: str, importance: float):
        if mem_id in self.memories:
            self.memories[mem_id].importance = importance
            self._save_memories()
    
    def delete_memory(self, mem_id: str) -> bool:
        if mem_id in self.memories:
            del self.memories[mem_id]
            self._save_memories()
            return True
        return False
    
    def clear_temporary(self):
        to_delete = [m_id for m_id, m in self.memories.items() if m.memory_type == "temporary"]
        for m_id in to_delete:
            del self.memories[m_id]
        self._save_memories()
    
    def get_context_window(self, max_tokens: int = 4000) -> List[Memory]:
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda m: (m.importance, m.accessed_at),
            reverse=True
        )
        
        result = []
        total_chars = 0
        max_chars = max_tokens * 4
        
        for memory in sorted_memories:
            if total_chars + len(memory.content) <= max_chars:
                result.append(memory)
                total_chars += len(memory.content)
            else:
                break
        
        return result
