"""
SDFAI Skill Manager - 技能管理器
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .skill_translator import SDFAISkill, OpenClawTranslator
from .skill_parser import SkillParser


class SkillManager:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.translator = OpenClawTranslator(skills_dir)
        self.parser = SkillParser()
        self.skills: Dict[str, SDFAISkill] = {}
        self.handlers: Dict[str, Callable] = {}
        self._load_skills()
    
    def _load_skills(self):
        installed_dir = self.skills_dir / "installed"
        if not installed_dir.exists():
            return
        
        for skill_dir in installed_dir.iterdir():
            if skill_dir.is_dir():
                skill = self.parser.parse_file(skill_dir / "skill.json")
                if skill:
                    self.skills[skill.name.lower().replace(' ', '_')] = skill
    
    def install_skill(self, source_path: Path) -> Optional[str]:
        skill = self.translator.install_skill(source_path)
        if skill:
            key = skill.name.lower().replace(' ', '_')
            self.skills[key] = skill
            return key
        return None
    
    def get_skill(self, name: str) -> Optional[SDFAISkill]:
        return self.skills.get(name.lower().replace(' ', '_'))
    
    def list_skills(self) -> List[Dict]:
        return [
            {
                "name": skill.name,
                "version": skill.version,
                "description": skill.description,
                "triggers_count": len(skill.triggers),
                "source_format": skill.source_format
            }
            for skill in self.skills.values()
        ]
    
    def register_handler(self, skill_name: str, handler: Callable):
        key = skill_name.lower().replace(' ', '_')
        self.handlers[key] = handler
    
    def match_trigger(self, text: str) -> Optional[tuple]:
        text_lower = text.lower()
        
        for key, skill in self.skills.items():
            for trigger in skill.triggers:
                if trigger.lower() in text_lower:
                    return (key, trigger, skill)
        
        return None
    
    async def execute(self, text: str, context: Dict = None) -> Optional[Any]:
        match = self.match_trigger(text)
        if not match:
            return None
        
        skill_key, trigger, skill = match
        
        if skill_key in self.handlers:
            handler = self.handlers[skill_key]
            if asyncio.iscoroutinefunction(handler):
                return await handler(text, trigger, skill, context)
            else:
                return handler(text, trigger, skill, context)
        
        results = []
        for action in skill.actions:
            action_type = action.get("type", "unknown")
            
            if action_type == "respond":
                results.append(action.get("text", ""))
            elif action_type == "execute":
                cmd = action.get("command", "")
                results.append(f"[Execute: {cmd}]")
            elif action_type == "raw":
                results.append(action.get("content", ""))
        
        return "\n".join(results) if results else None
    
    def reload_skills(self):
        self.skills.clear()
        self._load_skills()
