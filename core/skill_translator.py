"""
SDFAI Skill Translator - OpenClaw/Nanobot格式翻译为SDFAI格式
"""
import re
import json
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SDFAISkill:
    name: str
    version: str
    description: str
    triggers: List[str]
    actions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_format: str = "sdfai"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_markdown(self) -> str:
        md = f"""# {self.name}

## Metadata
- Version: {self.version}
- Description: {self.description}
- Source: {self.source_format}
- Created: {self.created_at.isoformat()}

## Triggers
"""
        for trigger in self.triggers:
            md += f"- `{trigger}`\n"
        
        md += "\n## Actions\n"
        for i, action in enumerate(self.actions, 1):
            md += f"\n### Action {i}\n"
            md += f"```json\n{json.dumps(action, ensure_ascii=False, indent=2)}\n```\n"
        
        if self.metadata:
            md += "\n## Additional Metadata\n"
            md += f"```json\n{json.dumps(self.metadata, ensure_ascii=False, indent=2)}\n```\n"
        
        return md
    
    def to_json(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "triggers": self.triggers,
            "actions": self.actions,
            "metadata": self.metadata,
            "source_format": self.source_format,
            "created_at": self.created_at.isoformat()
        }


class OpenClawTranslator:
    OPENCLAW_PATTERNS = {
        'skill_name': r'^#\s+(.+)$',
        'description': r'^##\s+Description\s*\n(.+?)(?=\n##|\Z)',
        'triggers': r'^##\s+Triggers\s*\n((?:[-*]\s+.+\n?)+)',
        'actions': r'^##\s+Actions\s*\n((?:[-*]\s+.+\n?)+)',
    }
    
    NANOBOT_PATTERNS = {
        'skill_name': r'^#\s+(.+)$',
        'description': r'^##\s+Description\s*\n(.+?)(?=\n##|\Z)',
        'commands': r'^##\s+Commands\s*\n((?:[-*]\s+.+\n?)+)',
        'responses': r'^##\s+Responses\s*\n((?:[-*]\s+.+\n?)+)',
    }
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.incoming_dir = skills_dir / "incoming"
        self.incoming_dir.mkdir(exist_ok=True)
        self.installed_dir = skills_dir / "installed"
        self.installed_dir.mkdir(exist_ok=True)
    
    def detect_format(self, content: str) -> str:
        if '## Triggers' in content and '## Actions' in content:
            return 'openclaw'
        elif '## Commands' in content or '## Responses' in content:
            return 'nanobot'
        elif content.strip().startswith('{'):
            try:
                json.loads(content)
                return 'json'
            except:
                pass
        return 'sdfai'
    
    def parse_openclaw(self, content: str) -> SDFAISkill:
        lines = content.split('\n')
        
        name = "Unknown Skill"
        for line in lines:
            match = re.match(self.OPENCLAW_PATTERNS['skill_name'], line)
            if match:
                name = match.group(1).strip()
                break
        
        desc_match = re.search(self.OPENCLAW_PATTERNS['description'], content, re.MULTILINE | re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""
        
        triggers = []
        triggers_match = re.search(self.OPENCLAW_PATTERNS['triggers'], content, re.MULTILINE)
        if triggers_match:
            for line in triggers_match.group(1).strip().split('\n'):
                trigger = re.sub(r'^[-*]\s+', '', line).strip()
                if trigger:
                    triggers.append(trigger)
        
        actions = []
        actions_match = re.search(self.OPENCLAW_PATTERNS['actions'], content, re.MULTILINE)
        if actions_match:
            for line in actions_match.group(1).strip().split('\n'):
                action_str = re.sub(r'^[-*]\s+', '', line).strip()
                if action_str:
                    actions.append({"type": "execute", "command": action_str})
        
        return SDFAISkill(
            name=name,
            version="1.0.0",
            description=description,
            triggers=triggers,
            actions=actions,
            source_format="openclaw"
        )
    
    def parse_nanobot(self, content: str) -> SDFAISkill:
        lines = content.split('\n')
        
        name = "Unknown Skill"
        for line in lines:
            match = re.match(self.NANOBOT_PATTERNS['skill_name'], line)
            if match:
                name = match.group(1).strip()
                break
        
        desc_match = re.search(self.NANOBOT_PATTERNS['description'], content, re.MULTILINE | re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""
        
        triggers = []
        commands_match = re.search(self.NANOBOT_PATTERNS['commands'], content, re.MULTILINE)
        if commands_match:
            for line in commands_match.group(1).strip().split('\n'):
                cmd = re.sub(r'^[-*]\s+', '', line).strip()
                if cmd:
                    triggers.append(cmd)
        
        actions = []
        responses_match = re.search(self.NANOBOT_PATTERNS['responses'], content, re.MULTILINE)
        if responses_match:
            for line in responses_match.group(1).strip().split('\n'):
                resp = re.sub(r'^[-*]\s+', '', line).strip()
                if resp:
                    actions.append({"type": "respond", "text": resp})
        
        return SDFAISkill(
            name=name,
            version="1.0.0",
            description=description,
            triggers=triggers,
            actions=actions,
            source_format="nanobot"
        )
    
    def parse_json(self, content: str) -> SDFAISkill:
        data = json.loads(content)
        return SDFAISkill(
            name=data.get("name", "Unknown"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            triggers=data.get("triggers", []),
            actions=data.get("actions", []),
            metadata=data.get("metadata", {}),
            source_format="json"
        )
    
    def translate(self, content: str) -> SDFAISkill:
        fmt = self.detect_format(content)
        
        if fmt == 'openclaw':
            return self.parse_openclaw(content)
        elif fmt == 'nanobot':
            return self.parse_nanobot(content)
        elif fmt == 'json':
            return self.parse_json(content)
        else:
            return SDFAISkill(
                name="Raw Skill",
                version="1.0.0",
                description=content[:200],
                triggers=[],
                actions=[{"type": "raw", "content": content}],
                source_format="raw"
            )
    
    def install_skill(self, source_path: Path) -> Optional[SDFAISkill]:
        if not source_path.exists():
            return None
        
        content = source_path.read_text(encoding='utf-8')
        skill = self.translate(content)
        
        skill_dir = self.installed_dir / skill.name.lower().replace(' ', '_')
        skill_dir.mkdir(exist_ok=True)
        
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill.to_markdown(), encoding='utf-8')
        
        json_file = skill_dir / "skill.json"
        json_file.write_text(json.dumps(skill.to_json(), ensure_ascii=False, indent=2), encoding='utf-8')
        
        return skill
    
    def list_installed_skills(self) -> List[Dict]:
        skills = []
        for skill_dir in self.installed_dir.iterdir():
            if skill_dir.is_dir():
                json_file = skill_dir / "skill.json"
                if json_file.exists():
                    try:
                        data = json.loads(json_file.read_text(encoding='utf-8'))
                        skills.append(data)
                    except:
                        pass
        return skills
