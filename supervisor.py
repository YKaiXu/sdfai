#!/usr/bin/env python3
"""
AI幻觉监督模块 - 独立运行，不阻塞主流程
使用Qwen3 1.7B监督Kimi输出
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import asyncssh

logger = logging.getLogger('supervisor')

REMOTE_HOST = "192.168.1.8"
REMOTE_USER = "yupeng"
REMOTE_PASS = "Ykx130729!"
REMOTE_DIR = "/home/yupeng/sdfai/sdfai"

QWEN_CONFIG = {
    "model_id": "xop3qwen1b7",
    "app_id": "980d8a95",
    "api_key": "f83bd2c5b262e94b45cb9f58bd304533",
    "api_secret": "ZDRhN2U5YWZlY2M4NzQ3ZDRmODE0OTAx",
    "ws_url": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat"
}


@dataclass
class SupervisionRecord:
    timestamp: str
    operation: str
    input_data: str
    ai_output: str
    actual_result: str
    is_valid: bool
    issues: list
    confidence: float


class AIHallucinationSupervisor:
    def __init__(self):
        self.records: list = []
        self._running = False
        self._qwen_gateway = None
    
    async def initialize(self):
        try:
            from qwen_gateway import QwenGateway, QwenConfig
            self._qwen_gateway = QwenGateway(QwenConfig(**QWEN_CONFIG))
            self._running = True
            logger.info("✅ AI幻觉监督模块已启动")
        except Exception as e:
            logger.warning(f"监督模块初始化失败: {e}")
    
    async def supervise_async(self, operation: str, input_data: str, ai_output: str, actual_result: str = None):
        """异步监督，不阻塞主流程"""
        if not self._running or not self._qwen_gateway:
            return
        
        # 创建异步任务，不等待结果
        asyncio.create_task(self._do_supervise(operation, input_data, ai_output, actual_result))
    
    async def _do_supervise(self, operation: str, input_data: str, ai_output: str, actual_result: str):
        """实际执行监督"""
        try:
            result = await self._qwen_gateway.supervise(operation, input_data, ai_output, actual_result)
            
            record = SupervisionRecord(
                timestamp=datetime.now().isoformat(),
                operation=operation,
                input_data=input_data[:200],
                ai_output=ai_output[:200],
                actual_result=actual_result[:200] if actual_result else "未验证",
                is_valid=result.is_valid,
                issues=result.issues,
                confidence=result.confidence
            )
            
            self.records.append(record)
            if len(self.records) > 100:
                self.records = self.records[-100:]
            
            # 记录日志
            if not result.is_valid:
                logger.warning(f"🚨 AI幻觉检测: {operation} - {result.issues}")
                # 可以在这里添加通知逻辑
            else:
                logger.debug(f"✅ 监督通过: {operation} (置信度: {result.confidence})")
                
        except Exception as e:
            logger.error(f"监督执行失败: {e}")
    
    def get_recent_issues(self, limit: int = 10) -> list:
        """获取最近的问题记录"""
        return [r for r in self.records if not r.is_valid][-limit:]
    
    async def verify_command_result(self, command: str, ai_claim: str, actual_result: str) -> bool:
        """验证命令执行结果是否与AI声称一致"""
        if not self._qwen_gateway:
            return True
        
        result = await self._qwen_gateway.supervise(
            operation="command_execution",
            input_data=command,
            ai_output=ai_claim,
            actual_result=actual_result
        )
        
        return result.is_valid


# 全局监督器实例
_supervisor: Optional[AIHallucinationSupervisor] = None


def get_supervisor() -> AIHallucinationSupervisor:
    global _supervisor
    if _supervisor is None:
        _supervisor = AIHallucinationSupervisor()
    return _supervisor


async def init_supervisor():
    """初始化监督器"""
    supervisor = get_supervisor()
    await supervisor.initialize()
    return supervisor
