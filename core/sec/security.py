"""
Security Manager - 安全管理器
硬编码安全规则，防止LLM绕过
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class SecurityLevel(Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class SecurityRule:
    name: str
    pattern: str
    level: SecurityLevel
    description: str
    action: str = "block"
    exceptions: List[str] = field(default_factory=list)


HARDCODED_SECURITY_RULES: List[SecurityRule] = [
    SecurityRule(
        name="rm_rf_root",
        pattern=r"rm\s+(-[rf]+\s+)+/*",
        level=SecurityLevel.CRITICAL,
        description="Attempt to delete root filesystem",
        action="block"
    ),
    SecurityRule(
        name="rm_rf_home",
        pattern=r"rm\s+(-[rf]+\s+)+~",
        level=SecurityLevel.CRITICAL,
        description="Attempt to delete home directory",
        action="block"
    ),
    SecurityRule(
        name="fork_bomb",
        pattern=r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",
        level=SecurityLevel.CRITICAL,
        description="Fork bomb detected",
        action="block"
    ),
    SecurityRule(
        name="dd_disk",
        pattern=r"dd\s+if=.*of=/dev/",
        level=SecurityLevel.CRITICAL,
        description="Attempt to overwrite disk",
        action="block"
    ),
    SecurityRule(
        name="mkfs",
        pattern=r"mkfs\s+",
        level=SecurityLevel.HIGH_RISK,
        description="Format filesystem command",
        action="confirm"
    ),
    SecurityRule(
        name="chmod_777",
        pattern=r"chmod\s+(-R\s+)?777",
        level=SecurityLevel.HIGH_RISK,
        description="Insecure permission setting",
        action="confirm"
    ),
    SecurityRule(
        name="curl_bash",
        pattern=r"curl\s+.*\|\s*(sudo\s+)?bash",
        level=SecurityLevel.HIGH_RISK,
        description="Remote code execution via curl",
        action="confirm"
    ),
]


class SecurityManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.command_rules = HARDCODED_SECURITY_RULES
        self.audit_log: List[Dict] = []
    
    def evaluate_command(self, command: str) -> SecurityLevel:
        highest_risk = SecurityLevel.SAFE
        
        for rule in self.command_rules:
            if re.search(rule.pattern, command, re.IGNORECASE):
                if self._compare_levels(rule.level, highest_risk) > 0:
                    highest_risk = rule.level
        
        return highest_risk
    
    def is_allowed(self, command: str, context: Dict = None) -> bool:
        level = self.evaluate_command(command)
        return level not in [SecurityLevel.CRITICAL, SecurityLevel.BLOCKED]
    
    def needs_confirmation(self, command: str) -> bool:
        level = self.evaluate_command(command)
        return level in [SecurityLevel.HIGH_RISK, SecurityLevel.MEDIUM_RISK]
    
    def get_action(self, level: SecurityLevel) -> str:
        actions = {
            SecurityLevel.SAFE: "allow",
            SecurityLevel.LOW_RISK: "log",
            SecurityLevel.MEDIUM_RISK: "confirm",
            SecurityLevel.HIGH_RISK: "confirm",
            SecurityLevel.CRITICAL: "block",
            SecurityLevel.BLOCKED: "block"
        }
        return actions.get(level, "block")
    
    def _compare_levels(self, a: SecurityLevel, b: SecurityLevel) -> int:
        levels = {
            SecurityLevel.SAFE: 0,
            SecurityLevel.LOW_RISK: 1,
            SecurityLevel.MEDIUM_RISK: 2,
            SecurityLevel.HIGH_RISK: 3,
            SecurityLevel.CRITICAL: 4,
            SecurityLevel.BLOCKED: 5
        }
        return levels.get(a, 0) - levels.get(b, 0)
