"""
Stability Manager - 稳定性管理器
监控系统稳定性，防止资源耗尽
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    import psutil
except ImportError:
    psutil = None


class StabilityStatus(Enum):
    STABLE = "stable"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_count: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StabilityThreshold:
    cpu_warning: float = 80.0
    cpu_critical: float = 95.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 85.0
    disk_critical: float = 95.0


class StabilityManager:
    def __init__(self, data_dir: Path, thresholds: StabilityThreshold = None):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.thresholds = thresholds or StabilityThreshold()
        self.metrics_history: List[SystemMetrics] = []
        self._monitoring = False
    
    def get_current_metrics(self) -> SystemMetrics:
        if psutil:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent if psutil.disk_usage('/') else 0
            process_count = len(psutil.pids())
        else:
            cpu, memory, disk, process_count = 0, 0, 0, 0
        
        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            disk_percent=disk,
            process_count=process_count
        )
    
    def evaluate_stability(self, metrics: SystemMetrics = None) -> StabilityStatus:
        if metrics is None:
            metrics = self.get_current_metrics()
        
        if self._is_emergency(metrics):
            return StabilityStatus.EMERGENCY
        elif self._is_critical(metrics):
            return StabilityStatus.CRITICAL
        elif self._is_warning(metrics):
            return StabilityStatus.WARNING
        
        return StabilityStatus.STABLE
    
    def _is_warning(self, m: SystemMetrics) -> bool:
        return (
            m.cpu_percent >= self.thresholds.cpu_warning or
            m.memory_percent >= self.thresholds.memory_warning or
            m.disk_percent >= self.thresholds.disk_warning
        )
    
    def _is_critical(self, m: SystemMetrics) -> bool:
        return (
            m.cpu_percent >= self.thresholds.cpu_critical or
            m.memory_percent >= self.thresholds.memory_critical or
            m.disk_percent >= self.thresholds.disk_critical
        )
    
    def _is_emergency(self, m: SystemMetrics) -> bool:
        return (
            m.cpu_percent >= 99.0 or
            m.memory_percent >= 99.0 or
            m.disk_percent >= 99.0
        )
    
    def can_execute_task(self, task_type: str = "normal") -> bool:
        status = self.evaluate_stability()
        
        if status == StabilityStatus.EMERGENCY:
            return False
        elif status == StabilityStatus.CRITICAL:
            return task_type == "critical"
        elif status == StabilityStatus.WARNING:
            return task_type in ["critical", "important"]
        
        return True
    
    def get_status_report(self) -> Dict[str, Any]:
        metrics = self.get_current_metrics()
        status = self.evaluate_stability(metrics)
        
        return {
            "status": status.value,
            "metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "process_count": metrics.process_count
            },
            "can_execute": self.can_execute_task()
        }
