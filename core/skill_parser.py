"""
SDFAI Skill Parser - 解析SDFAI原生技能格式
"""
import re
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .skill_translator import SDFAISkill


class SkillParser:
    SDFAI_PATTERNS = {
        'skill_name': r'^#\s+(.+)$',
        'version': r'^-\s+Version:\s*(.+)$',
        'description': r'^-\s+Description:\s*(.+)$',
        'source': r'^-\s+Source:\s*(.+)$',
        'triggers_section': r'^##\s+Triggers\s*$',
        'actions_section': r'^##\s+Actions\s*$',
        'list_item': r'^-\s+`?(.+?)`?\s*$',
        'json_block': r'```json\s*\n(.+?)\n```',
    }
    
    def parse_markdown(self, content: str) -> Optional[SDFAISkill]:
        lines = content.split('\n')
        
        name = None
        version = "1.0.0"
        description = ""
        source_format = "sdfai"
        triggers = []
        actions = []
        
        current_section = None
        
        for i, line in enumerate(lines):
            name_match = re.match(self.SDAI_PATTERNS['skill_name'], line)
            if name_match and name is None:
                name = name_match.group(1).strip()
                continue
            
            if line.startswith('- Version:'):
                version = line.split(':', 1)[1].strip()
                continue
            
            if line.startswith('- Description:'):
                description = line.split(':', 1)[1].strip()
                continue
            
            if line.startswith('- Source:'):
                source_format = line.split(':', 1)[1].strip()
                continue
            
            if line.startswith('## Triggers'):
                current_section = 'triggers'
                continue
            
            if line.startswith('## Actions'):
                current_section = 'actions'
                continue
            
            if current_section == 'triggers':
                item_match = re.match(self.SDAI_PATTERNS['list_item'], line)
                if item_match:
                    triggers.append(item_match.group(1).strip())
            
            if current_section == 'actions':
                json_match = re.search(self.SDAI_PATTERNS['json_block'], content[content.find(line):], re.DOTALL)
                if json_match and 'Action' in line:
                    try:
                        action_data = json.loads(json_match.group(1))
                        actions.append(action_data)
                    except:
                        pass
        
        if name is None:
            return None
        
        return SDFAISkill(
            name=name,
            version=version,
            description=description,
            triggers=triggers,
            actions=actions,
            source_format=source_format
        )
    
    def parse_json(self, content: str) -> Optional[SDFAISkill]:
        try:
            data = json.loads(content)
            return SDFAISkill(
                name=data["name"],
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                triggers=data.get("triggers", []),
                actions=data.get("actions", []),
                metadata=data.get("metadata", {}),
                source_format=data.get("source_format", "sdfai"),
                created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
            )
        except:
            return None
    
    def parse_file(self, path: Path) -> Optional[SDFAISkill]:
        if not path.exists():
            return None
        
        content = path.read_text(encoding='utf-8')
        
        if path.suffix == '.json':
            return self.parse_json(content)
        elif path.suffix == '.md':
            return self.parse_markdown(content)
        
        return None
