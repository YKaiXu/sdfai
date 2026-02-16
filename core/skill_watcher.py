"""
SDFAI Skill Watcher - 技能文件监控器
监测OpenClaw skill格式文件上传，询问用户确认后安装
"""
import asyncio
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .skill_translator import OpenClawTranslator, SDFAISkill


@dataclass
class PendingSkill:
    path: Path
    detected_at: datetime
    format: str
    skill_name: str
    confirmed: bool = False
    installed: bool = False
    hash: str = ""


class SkillFileHandler(FileSystemEventHandler):
    def __init__(self, watcher: 'SkillWatcher'):
        self.watcher = watcher
        self.processed_hashes: Set[str] = set()
    
    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if self._is_skill_file(path):
            asyncio.create_task(self.watcher.on_skill_detected(path))
    
    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if self._is_skill_file(path):
            file_hash = self._get_file_hash(path)
            if file_hash not in self.processed_hashes:
                asyncio.create_task(self.watcher.on_skill_detected(path))
    
    def _is_skill_file(self, path: Path) -> bool:
        if path.suffix not in ['.md', '.json']:
            return False
        
        if path.name.startswith('.'):
            return False
        
        if '__pycache__' in str(path):
            return False
        
        return True
    
    def _get_file_hash(self, path: Path) -> str:
        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except:
            return ""


class SkillWatcher:
    def __init__(
        self, 
        skills_dir: Path,
        translator: OpenClawTranslator,
        im_notifier: Callable = None
    ):
        self.skills_dir = skills_dir
        self.translator = translator
        self.im_notifier = im_notifier
        
        self.incoming_dir = skills_dir / "incoming"
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        
        self.pending_skills: Dict[str, PendingSkill] = {}
        self.observer: Optional[Observer] = None
        self._running = False
    
    def start(self):
        if self._running:
            return
        
        handler = SkillFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.incoming_dir), recursive=True)
        self.observer.start()
        self._running = True
        
        self._scan_existing_files()
    
    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self._running = False
    
    def _scan_existing_files(self):
        for path in self.incoming_dir.rglob("*"):
            if path.is_file() and path.suffix in ['.md', '.json']:
                asyncio.create_task(self.on_skill_detected(path))
    
    async def on_skill_detected(self, path: Path):
        try:
            content = path.read_text(encoding='utf-8')
            fmt = self.translator.detect_format(content)
            
            if fmt == 'sdfai' and '## Triggers' not in content:
                return
            
            skill = self.translator.translate(content)
            
            pending = PendingSkill(
                path=path,
                detected_at=datetime.now(),
                format=fmt,
                skill_name=skill.name,
                hash=self._get_file_hash(path)
            )
            
            pending_id = f"{skill.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.pending_skills[pending_id] = pending
            
            await self._notify_user(pending_id, pending)
            
        except Exception as e:
            print(f"Error detecting skill: {e}")
    
    async def _notify_user(self, pending_id: str, pending: PendingSkill):
        if self.im_notifier:
            message = self._format_confirmation_message(pending_id, pending)
            await self.im_notifier(message, {"type": "skill_install_request", "pending_id": pending_id})
    
    def _format_confirmation_message(self, pending_id: str, pending: PendingSkill) -> str:
        return f"""
📥 检测到新的OpenClaw技能

技能名称: {pending.skill_name}
格式: {pending.format}
文件: {pending.path.name}
检测时间: {pending.detected_at.strftime('%Y-%m-%d %H:%M:%S')}

是否安装此技能？
回复 "install {pending_id}" 确认安装
回复 "reject {pending_id}" 拒绝安装
"""
    
    async def confirm_install(self, pending_id: str) -> bool:
        if pending_id not in self.pending_skills:
            return False
        
        pending = self.pending_skills[pending_id]
        pending.confirmed = True
        
        skill = self.translator.install_skill(pending.path)
        if skill:
            pending.installed = True
            
            if self.im_notifier:
                await self.im_notifier(
                    f"✅ 技能 '{skill.name}' 已成功安装！\n触发词: {', '.join(skill.triggers[:5])}",
                    {"type": "skill_installed", "skill_name": skill.name}
                )
            
            return True
        
        return False
    
    async def reject_install(self, pending_id: str) -> bool:
        if pending_id not in self.pending_skills:
            return False
        
        pending = self.pending_skills[pending_id]
        
        if self.im_notifier:
            await self.im_notifier(
                f"❌ 技能 '{pending.skill_name}' 安装已取消",
                {"type": "skill_rejected", "skill_name": pending.skill_name}
            )
        
        del self.pending_skills[pending_id]
        return True
    
    def _get_file_hash(self, path: Path) -> str:
        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except:
            return ""
    
    def get_pending_skills(self) -> List[Dict]:
        return [
            {
                "id": pid,
                "name": p.skill_name,
                "format": p.format,
                "detected_at": p.detected_at.isoformat(),
                "confirmed": p.confirmed,
                "installed": p.installed
            }
            for pid, p in self.pending_skills.items()
        ]
    
    def is_running(self) -> bool:
        return self._running
