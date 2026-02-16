#!/usr/bin/env python3
"""
LLM故障转移管理器
当主LLM失效时自动切换到备用LLM
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger('llm_failover')


@dataclass
class LLMStatus:
    name: str
    is_healthy: bool
    last_success: datetime
    failure_count: int
    is_primary: bool


class LLMFailoverManager:
    def __init__(self, primary_llm, fallback_llm):
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm
        self.current_llm = primary_llm
        self.is_using_fallback = False
        
        self.primary_status = LLMStatus(
            name="Kimi-K2-5",
            is_healthy=True,
            last_success=datetime.now(),
            failure_count=0,
            is_primary=True
        )
        
        self.fallback_status = LLMStatus(
            name="Qwen3-1.7B",
            is_healthy=True,
            last_success=datetime.now(),
            failure_count=0,
            is_primary=False
        )
        
        self.max_failures = 3
        self.recovery_interval = timedelta(minutes=5)
    
    async def chat(self, message: str, **kwargs):
        """带故障转移的聊天"""
        # 尝试当前LLM
        try:
            response = await self.current_llm.chat(message, **kwargs)
            self._record_success()
            return response
        except Exception as e:
            logger.error(f"LLM错误 ({self._get_current_name()}): {e}")
            self._record_failure()
            
            # 如果主LLM失败，切换到备用
            if not self.is_using_fallback and self.fallback_llm:
                logger.warning("⚠️ 主LLM失败，切换到备用LLM (Qwen)")
                self.is_using_fallback = True
                self.current_llm = self.fallback_llm
                
                try:
                    response = await self.current_llm.chat(message, **kwargs)
                    self._record_success(is_fallback=True)
                    return response
                except Exception as e2:
                    logger.error(f"备用LLM也失败: {e2}")
                    raise e2
            else:
                raise e
    
    def _get_current_name(self) -> str:
        return "Qwen" if self.is_using_fallback else "Kimi"
    
    def _record_success(self, is_fallback: bool = False):
        status = self.fallback_status if is_fallback else self.primary_status
        status.is_healthy = True
        status.last_success = datetime.now()
        status.failure_count = 0
        
        # 如果备用LLM成功，检查是否可以恢复主LLM
        if is_fallback and self.primary_status.failure_count >= self.max_failures:
            if datetime.now() - self.primary_status.last_success > self.recovery_interval:
                logger.info("🔄 尝试恢复主LLM...")
                self.is_using_fallback = False
                self.current_llm = self.primary_llm
    
    def _record_failure(self):
        if self.is_using_fallback:
            self.fallback_status.failure_count += 1
            self.fallback_status.is_healthy = False
        else:
            self.primary_status.failure_count += 1
            self.primary_status.is_healthy = False
    
    def get_status(self) -> dict:
        return {
            "current_llm": self._get_current_name(),
            "is_using_fallback": self.is_using_fallback,
            "primary": {
                "name": self.primary_status.name,
                "healthy": self.primary_status.is_healthy,
                "failures": self.primary_status.failure_count
            },
            "fallback": {
                "name": self.fallback_status.name,
                "healthy": self.fallback_status.is_healthy,
                "failures": self.fallback_status.failure_count
            }
        }
