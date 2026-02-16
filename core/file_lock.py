"""
SDFAI File Lock - 文件锁定机制
防止AI修改已测试通过的核心文件
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileLock:
    filepath: str
    checksum: str
    locked_at: datetime
    locked_by: str = "system"
    reason: str = "tested_and_verified"
    allow_ai_modify: bool = False


CORE_LOCKED_FILES = [
    "channel/base.py",
    "channel/__init__.py",
    "core/__init__.py",
    "core/ai_engine.py",
    "core/router.py",
    "core/daemon.py",
    "core/memory.py",
    "core/message_queue.py",
    "core/thread_manager.py",
    "core/sec/__init__.py",
    "core/sec/security.py",
    "core/sec/stability.py",
    "core/sec/evaluator.py",
    "core/sec/hardening.py",
    "sdf/__init__.py",
    "sdf/client.py",
    "sdf/commands.py",
    "sdf/connection.py",
    "memory/__init__.py",
    "memory/base.py",
    "memory/sqlite.py",
    "memory/vector.py",
    "memory/file.py",
    "skills/__init__.py",
]

MODIFIABLE_FILES = [
    "skills/installed/",
    "skills/incoming/",
    "data/",
    "logs/",
    "sdfai_config.json",
]


class FileLockManager:
    def __init__(self, sdfai_dir: Path, lock_file: Path = None):
        self.sdfai_dir = sdfai_dir
        self.lock_file = lock_file or sdfai_dir / ".sdfai_lock"
        self.locks: Dict[str, FileLock] = {}
        self._load_locks()
    
    def _load_locks(self):
        if self.lock_file.exists():
            try:
                data = json.loads(self.lock_file.read_text(encoding='utf-8'))
                for filepath, lock_data in data.items():
                    self.locks[filepath] = FileLock(
                        filepath=filepath,
                        checksum=lock_data["checksum"],
                        locked_at=datetime.fromisoformat(lock_data["locked_at"]),
                        locked_by=lock_data.get("locked_by", "system"),
                        reason=lock_data.get("reason", "tested_and_verified"),
                        allow_ai_modify=lock_data.get("allow_ai_modify", False)
                    )
            except:
                pass
    
    def _save_locks(self):
        data = {}
        for filepath, lock in self.locks.items():
            data[filepath] = {
                "checksum": lock.checksum,
                "locked_at": lock.locked_at.isoformat(),
                "locked_by": lock.locked_by,
                "reason": lock.reason,
                "allow_ai_modify": lock.allow_ai_modify
            }
        self.lock_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    def _calculate_checksum(self, filepath: str) -> str:
        full_path = self.sdfai_dir / filepath
        if not full_path.exists():
            return ""
        
        content = full_path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    
    def lock_file(self, filepath: str, reason: str = "tested_and_verified") -> bool:
        checksum = self._calculate_checksum(filepath)
        if not checksum:
            return False
        
        self.locks[filepath] = FileLock(
            filepath=filepath,
            checksum=checksum,
            locked_at=datetime.now(),
            reason=reason
        )
        self._save_locks()
        return True
    
    def unlock_file(self, filepath: str) -> bool:
        if filepath in self.locks:
            del self.locks[filepath]
            self._save_locks()
            return True
        return False
    
    def is_locked(self, filepath: str) -> bool:
        return filepath in self.locks
    
    def can_ai_modify(self, filepath: str) -> bool:
        for pattern in MODIFIABLE_FILES:
            if pattern in filepath:
                return True
        
        if filepath in self.locks:
            return self.locks[filepath].allow_ai_modify
        
        return False
    
    def verify_integrity(self, filepath: str) -> bool:
        if filepath not in self.locks:
            return True
        
        current_checksum = self._calculate_checksum(filepath)
        return current_checksum == self.locks[filepath].checksum
    
    def verify_all_integrity(self) -> Dict[str, bool]:
        results = {}
        for filepath in self.locks:
            results[filepath] = self.verify_integrity(filepath)
        return results
    
    def lock_all_core_files(self) -> int:
        locked_count = 0
        for filepath in CORE_LOCKED_FILES:
            if self.lock_file(filepath):
                locked_count += 1
        return locked_count
    
    def get_lock_info(self, filepath: str) -> Optional[FileLock]:
        return self.locks.get(filepath)
    
    def get_all_locks(self) -> Dict[str, FileLock]:
        return self.locks.copy()


def check_file_modification_allowed(filepath: str, sdfai_dir: Path) -> tuple:
    lock_manager = FileLockManager(sdfai_dir)
    
    if lock_manager.can_ai_modify(filepath):
        return True, "文件允许修改"
    
    if lock_manager.is_locked(filepath):
        lock_info = lock_manager.get_lock_info(filepath)
        return False, f"文件已锁定: {lock_info.reason if lock_info else 'unknown'}"
    
    return True, "文件未锁定"


def verify_core_files_integrity(sdfai_dir: Path) -> Dict[str, bool]:
    lock_manager = FileLockManager(sdfai_dir)
    
    if not lock_manager.locks:
        lock_manager.lock_all_core_files()
    
    return lock_manager.verify_all_integrity()
