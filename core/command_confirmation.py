"""
Command Confirmation - 命令确认机制
硬编码规则：用户输入错误或模糊指令时，提示用户确认后再执行
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ConfirmationStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class PendingConfirmation:
    confirmation_id: str
    original_input: str
    suggested_command: str
    command_type: str
    reason: str
    created_at: datetime = field(default_factory=datetime.now)
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    user_response: Optional[str] = None


HARDCODED_CONFIRMATION_RULES = {
    "REQUIRE_CONFIRMATION": True,
    "CONFIRMATION_TIMEOUT": 60,
    "MAX_PENDING_CONFIRMATIONS": 10,
    "MODIFIABLE": False
}


class CommandConfirmation:
    """
    命令确认机制 - 硬编码规则
    用户输入错误或模糊指令时，提示用户确认后再执行
    """
    
    HARDCODED_CONFIG = {
        "require_confirmation": True,
        "timeout_seconds": 60,
        "max_pending": 10,
        "modifiable": False
    }
    
    FUZZY_PATTERNS = {
        "room_switch": {
            "patterns": [
                r"切换.*房间",
                r"去.*房间",
                r"进入.*房间",
                r"切换.*聊天室",
                r"去.*聊天室",
                r"进入.*聊天室",
                r"换到.*",
                r"跳转.*",
            ],
            "extract": r"(?:切换到?|去|进入|换到|跳转到?)\s*(\S+)",
            "template": "g: {room}",
            "type": "room_switch"
        },
        "private_message": {
            "patterns": [
                r"私聊.*说",
                r"给.*发.*",
                r"告诉.*",
                r"私信.*",
                r"悄悄话.*",
            ],
            "extract": r"(?:私聊|给|告诉|私信)(\S+?)(?:说|发|，|,)\s*(.+)",
            "template": "s: {user} {message}",
            "type": "private_message"
        },
        "com_message": {
            "patterns": [
                r"发送.*到com",
                r"在com.*说",
                r"com.*发.*",
                r"群发.*",
            ],
            "extract": r"(?:发送|说|发)\s*(.+?)(?:到com|到群|到房间)",
            "template": "com: {message}",
            "type": "com_message"
        },
        "shell_command": {
            "patterns": [
                r"执行.*命令",
                r"运行.*",
                r"跑.*命令",
            ],
            "extract": r"(?:执行|运行|跑)\s*(.+)",
            "template": "sh: {command}",
            "type": "shell_command"
        }
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._pending: Dict[str, PendingConfirmation] = {}
        self._history: List[Dict] = []
    
    def analyze_input(self, user_input: str) -> Optional[PendingConfirmation]:
        user_input = user_input.strip()
        
        if self._has_explicit_prefix(user_input):
            return None
        
        for cmd_type, config in self.FUZZY_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, user_input):
                    extract_match = re.search(config["extract"], user_input)
                    
                    if extract_match:
                        suggested = self._build_command(
                            config["template"],
                            extract_match.groups()
                        )
                        
                        return self._create_confirmation(
                            user_input,
                            suggested,
                            cmd_type,
                            f"检测到可能的{self._get_type_name(cmd_type)}指令"
                        )
        
        return None
    
    def _has_explicit_prefix(self, text: str) -> bool:
        prefixes = ["com:", "sh:", "g:", "s:"]
        return any(text.startswith(p) for p in prefixes)
    
    def _build_command(self, template: str, groups: Tuple) -> str:
        result = template
        for i, group in enumerate(groups):
            if group:
                result = result.replace(f"{{{['room', 'user', 'message', 'command'][i] if i < 4 else i}}}", group)
        return result
    
    def _get_type_name(self, cmd_type: str) -> str:
        names = {
            "room_switch": "房间切换",
            "private_message": "私聊消息",
            "com_message": "COM消息",
            "shell_command": "Shell命令"
        }
        return names.get(cmd_type, cmd_type)
    
    def _create_confirmation(
        self,
        original: str,
        suggested: str,
        cmd_type: str,
        reason: str
    ) -> PendingConfirmation:
        import uuid
        confirmation_id = f"conf_{uuid.uuid4().hex[:8]}"
        
        confirmation = PendingConfirmation(
            confirmation_id=confirmation_id,
            original_input=original,
            suggested_command=suggested,
            command_type=cmd_type,
            reason=reason
        )
        
        self._pending[confirmation_id] = confirmation
        self._cleanup_old_confirmations()
        
        return confirmation
    
    def confirm(self, confirmation_id: str) -> Optional[PendingConfirmation]:
        if confirmation_id not in self._pending:
            return None
        
        confirmation = self._pending[confirmation_id]
        confirmation.status = ConfirmationStatus.CONFIRMED
        confirmation.user_response = "confirmed"
        
        self._save_to_history(confirmation)
        del self._pending[confirmation_id]
        
        return confirmation
    
    def reject(self, confirmation_id: str) -> Optional[PendingConfirmation]:
        if confirmation_id not in self._pending:
            return None
        
        confirmation = self._pending[confirmation_id]
        confirmation.status = ConfirmationStatus.REJECTED
        confirmation.user_response = "rejected"
        
        self._save_to_history(confirmation)
        del self._pending[confirmation_id]
        
        return confirmation
    
    def get_pending(self, confirmation_id: str) -> Optional[PendingConfirmation]:
        return self._pending.get(confirmation_id)
    
    def get_all_pending(self) -> List[PendingConfirmation]:
        return list(self._pending.values())
    
    def _cleanup_old_confirmations(self):
        now = datetime.now()
        expired = []
        
        for cid, conf in self._pending.items():
            age = (now - conf.created_at).total_seconds()
            if age > self.HARDCODED_CONFIG["timeout_seconds"]:
                conf.status = ConfirmationStatus.TIMEOUT
                expired.append(cid)
        
        for cid in expired:
            self._save_to_history(self._pending[cid])
            del self._pending[cid]
        
        while len(self._pending) > self.HARDCODED_CONFIG["max_pending"]:
            oldest = min(self._pending.items(), key=lambda x: x[1].created_at)
            del self._pending[oldest[0]]
    
    def _save_to_history(self, confirmation: PendingConfirmation):
        self._history.append({
            "id": confirmation.confirmation_id,
            "original": confirmation.original_input,
            "suggested": confirmation.suggested_command,
            "type": confirmation.command_type,
            "status": confirmation.status.value,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self._history) > 100:
            self._history = self._history[-100:]
        
        history_file = self.data_dir / "confirmation_history.json"
        history_file.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def format_confirmation_request(self, confirmation: PendingConfirmation) -> str:
        return f"""
⚠️ 指令确认请求

您的输入: "{confirmation.original_input}"
识别为: {self._get_type_name(confirmation.command_type)}
建议指令: `{confirmation.suggested_command}`

━━━━━━━━━━━━━━━━━━━━━━
回复 "confirm {confirmation.confirmation_id}" 确认执行
回复 "reject {confirmation.confirmation_id}" 取消
回复 "cancel" 取消所有待确认
━━━━━━━━━━━━━━━━━━━━━━
"""
