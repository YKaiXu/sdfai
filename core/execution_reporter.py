"""
Execution Reporter - 执行结果报告器
硬编码规则：所有特殊指令执行后，必须向指令发出的IM报告执行结果
"""
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ReportType(Enum):
    COM_MESSAGE_SENT = "com_message_sent"
    SHELL_EXECUTED = "shell_executed"
    ROOM_SWITCHED = "room_switched"
    PRIVATE_SENT = "private_sent"
    ERROR = "error"


HARDCODED_REPORT_RULES = {
    "REPORT_ENABLED": True,
    "REPORT_TO_SOURCE": True,
    "INCLUDE_TIMESTAMP": True,
    "INCLUDE_NCURSES_TIMESTAMP": True,
    "MODIFIABLE": False
}


@dataclass
class ExecutionReport:
    report_type: ReportType
    source_im: str
    source_user: str
    command: str
    success: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    ncurses_timestamp: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_message(self) -> str:
        if self.report_type == ReportType.COM_MESSAGE_SENT:
            ts_info = f"\n送达时间: {self.ncurses_timestamp}" if self.ncurses_timestamp else ""
            return f"✅ COM消息已发送\n命令: {self.command}\n内容: {self.message[:50]}...{ts_info}"
        
        elif self.report_type == ReportType.SHELL_EXECUTED:
            status = "成功" if self.success else "失败"
            return f"{'✅' if self.success else '❌'} Shell命令执行{status}\n命令: {self.command}\n结果: {self.message[:100]}"
        
        elif self.report_type == ReportType.ROOM_SWITCHED:
            return f"✅ 已切换到房间: {self.message}"
        
        elif self.report_type == ReportType.PRIVATE_SENT:
            return f"✅ 私聊消息已发送给: {self.message}"
        
        elif self.report_type == ReportType.ERROR:
            return f"❌ 执行失败: {self.message}"
        
        return f"执行结果: {self.message}"


class ExecutionReporter:
    """
    执行结果报告器 - 硬编码规则
    所有特殊指令执行后，必须向指令发出的IM报告执行结果
    """
    
    HARDCODED_CONFIG = {
        "report_enabled": True,
        "report_to_source": True,
        "include_ncurses_timestamp": True,
        "modifiable": False
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._report_history: list = []
    
    def create_report(
        self,
        report_type: ReportType,
        source_im: str,
        source_user: str,
        command: str,
        success: bool,
        message: str,
        ncurses_timestamp: str = None,
        details: dict = None
    ) -> ExecutionReport:
        report = ExecutionReport(
            report_type=report_type,
            source_im=source_im,
            source_user=source_user,
            command=command,
            success=success,
            message=message,
            ncurses_timestamp=ncurses_timestamp,
            details=details or {}
        )
        
        self._save_report(report)
        return report
    
    def report_com_sent(
        self,
        source_im: str,
        source_user: str,
        command: str,
        content: str,
        ncurses_timestamp: str = None
    ) -> ExecutionReport:
        return self.create_report(
            report_type=ReportType.COM_MESSAGE_SENT,
            source_im=source_im,
            source_user=source_user,
            command=command,
            success=True,
            message=content,
            ncurses_timestamp=ncurses_timestamp
        )
    
    def report_shell_executed(
        self,
        source_im: str,
        source_user: str,
        command: str,
        success: bool,
        output: str
    ) -> ExecutionReport:
        return self.create_report(
            report_type=ReportType.SHELL_EXECUTED,
            source_im=source_im,
            source_user=source_user,
            command=command,
            success=success,
            message=output
        )
    
    def report_room_switched(
        self,
        source_im: str,
        source_user: str,
        room: str,
        success: bool = True
    ) -> ExecutionReport:
        return self.create_report(
            report_type=ReportType.ROOM_SWITCHED,
            source_im=source_im,
            source_user=source_user,
            command=f"g: {room}",
            success=success,
            message=room
        )
    
    def report_private_sent(
        self,
        source_im: str,
        source_user: str,
        target_user: str,
        content: str,
        success: bool = True
    ) -> ExecutionReport:
        return self.create_report(
            report_type=ReportType.PRIVATE_SENT,
            source_im=source_im,
            source_user=source_user,
            command=f"s: {target_user}",
            success=success,
            message=target_user,
            details={"content": content}
        )
    
    def _save_report(self, report: ExecutionReport):
        self._report_history.append({
            "type": report.report_type.value,
            "source_im": report.source_im,
            "source_user": report.source_user,
            "command": report.command,
            "success": report.success,
            "timestamp": report.timestamp.isoformat(),
            "ncurses_timestamp": report.ncurses_timestamp
        })
        
        if len(self._report_history) > 100:
            self._report_history = self._report_history[-100:]
        
        report_file = self.data_dir / "execution_reports.json"
        report_file.write_text(
            json.dumps(self._report_history, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def get_config(self) -> Dict:
        return {
            "hardcoded_rules": self.HARDCODED_CONFIG,
            "warning": "These rules are hardcoded and cannot be modified by LLM"
        }
