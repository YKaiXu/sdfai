"""
Server Security Hardening - 服务器安全加强模块
通过IM通知用户并获取确认授权后执行安全加强操作
"""
import asyncio
import json
import subprocess
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SecurityCategory(Enum):
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    FILE_SYSTEM = "file_system"
    PROCESS = "process"
    SERVICE = "service"
    FIREWALL = "firewall"


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class OperationStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SecurityCheck:
    id: str
    category: SecurityCategory
    name: str
    description: str
    check_command: str
    expected_result: str
    remediation: str
    risk_level: RiskLevel
    auto_fix: bool = False
    fix_command: str = ""
    requires_confirm: bool = True


@dataclass
class PendingOperation:
    operation_id: str
    operation_type: str
    description: str
    command: str
    rollback_command: str
    risk_level: RiskLevel
    created_at: datetime
    status: OperationStatus = OperationStatus.PENDING
    confirmed_by: Optional[str] = None
    requires_sudo: bool = False


SAFE_SECURITY_CHECKS: List[SecurityCheck] = [
    SecurityCheck(
        id="AUTH001",
        category=SecurityCategory.AUTHENTICATION,
        name="SSH Root Login Check",
        description="Check if SSH root login is disabled",
        check_command="grep -E '^#?PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null || echo 'not_found'",
        expected_result="PermitRootLogin no",
        remediation="Disable SSH root login",
        risk_level=RiskLevel.HIGH,
        auto_fix=True,
        fix_command="sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config",
        requires_confirm=True
    ),
    SecurityCheck(
        id="FW001",
        category=SecurityCategory.FIREWALL,
        name="Firewall Status",
        description="Check if firewall is active",
        check_command="ufw status 2>/dev/null || echo 'ufw_not_installed'",
        expected_result="Status: active",
        remediation="Enable firewall",
        risk_level=RiskLevel.HIGH,
        auto_fix=True,
        fix_command="ufw --force enable",
        requires_confirm=True
    ),
]


class ServerSecurityHardening:
    def __init__(self, data_dir: Path, im_notifier: Callable = None):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.im_notifier = im_notifier
        self.pending_operations: Dict[str, PendingOperation] = {}
    
    async def run_assessment(self) -> Dict:
        findings = []
        
        for check in SAFE_SECURITY_CHECKS:
            finding = await self._run_check(check)
            if finding:
                findings.append(finding)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_findings": len(findings),
            "findings": findings
        }
    
    async def _run_check(self, check: SecurityCheck) -> Optional[Dict]:
        try:
            result = subprocess.run(
                check.check_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_state = result.stdout.strip()
            passed = self._evaluate_check_result(check, current_state)
            
            if not passed:
                return {
                    "id": check.id,
                    "name": check.name,
                    "category": check.category.value,
                    "risk_level": check.risk_level.value,
                    "current_state": current_state[:500],
                    "expected_state": check.expected_result,
                    "remediation": check.remediation,
                    "auto_fixable": check.auto_fix
                }
            
            return None
            
        except Exception as e:
            return None
    
    def _evaluate_check_result(self, check: SecurityCheck, result: str) -> bool:
        if check.id == "AUTH001":
            return "no" in result.lower() or result.strip() == ""
        elif check.id == "FW001":
            return "active" in result.lower()
        return True
    
    async def request_fix(self, finding_id: str) -> Optional[str]:
        check = next((c for c in SAFE_SECURITY_CHECKS if c.id == finding_id), None)
        if not check or not check.auto_fix:
            return None
        
        operation_id = f"op_{datetime.now().strftime('%Y%m%d%H%M%S')}_{finding_id}"
        
        operation = PendingOperation(
            operation_id=operation_id,
            operation_type="security_fix",
            description=f"Fix: {check.name}",
            command=check.fix_command,
            rollback_command="",
            risk_level=check.risk_level,
            created_at=datetime.now(),
            requires_sudo=self._check_requires_sudo(check.fix_command)
        )
        
        self.pending_operations[operation_id] = operation
        
        await self._request_user_confirmation(operation)
        
        return operation_id
    
    def _check_requires_sudo(self, command: str) -> bool:
        sudo_patterns = ["/etc/", "systemctl", "ufw", "apt", "chmod", "chown"]
        return any(p in command for p in sudo_patterns)
    
    async def _request_user_confirmation(self, operation: PendingOperation):
        if self.im_notifier:
            sudo_info = "\n\n⚠️ 此操作需要sudo权限" if operation.requires_sudo else ""
            message = f"""
🔒 安全操作确认请求

【问题描述】
{operation.description}

【操作详情】
执行命令: `{operation.command}`

【操作ID】
{operation.operation_id}

【风险级别】
{operation.risk_level.value}{sudo_info}

━━━━━━━━━━━━━━━━━━━━━━
回复 "confirm {operation.operation_id}" 确认执行
回复 "sudo {operation.operation_id} <密码>" 确认并提供sudo密码
回复 "reject {operation.operation_id}" 取消操作
━━━━━━━━━━━━━━━━━━━━━━
"""
            await self.im_notifier(message, {"type": "security_operation"})
    
    async def confirm_operation(self, operation_id: str, confirmed_by: str = "user", sudo_password: str = None) -> bool:
        if operation_id not in self.pending_operations:
            return False
        
        operation = self.pending_operations[operation_id]
        operation.status = OperationStatus.CONFIRMED
        operation.confirmed_by = confirmed_by
        
        result = await self._execute_operation(operation, sudo_password)
        return result
    
    async def _execute_operation(self, operation: PendingOperation, sudo_password: str = None) -> bool:
        try:
            command = operation.command
            
            if operation.requires_sudo and sudo_password:
                command = f"echo '{sudo_password}' | sudo -S {operation.command}"
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                operation.status = OperationStatus.COMPLETED
                return True
            else:
                operation.status = OperationStatus.FAILED
                return False
                
        except Exception as e:
            operation.status = OperationStatus.FAILED
            return False
