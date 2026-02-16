"""
Xunfei Channel - 讯飞LLM通讯通道
"""
import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Optional
from datetime import datetime

from .base import Channel, ChannelMessage, ChannelType


class XunfeiChannel(Channel):
    def __init__(self, channel_id: str, data_dir: Path, config: dict):
        super().__init__(channel_id, data_dir)
        self.config = config
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.app_id = config.get("app_id", "")
        self.model = config.get("model", "kimi")
        self._connected = False
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.XUNFEI
    
    async def connect(self) -> bool:
        self._connected = True
        self.save_status({
            "connected": True,
            "connected_at": datetime.now().isoformat(),
            "model": self.model
        })
        return True
    
    async def disconnect(self) -> bool:
        self._connected = False
        self.save_status({"connected": False})
        return True
    
    async def send(self, message: ChannelMessage) -> bool:
        self.write_to_outbox(message)
        return True
    
    async def receive(self) -> AsyncIterator[ChannelMessage]:
        while self._running:
            await asyncio.sleep(0.1)
            yield None
    
    async def chat(self, prompt: str, context: list = None) -> str:
        return f"[Xunfei] Response to: {prompt[:50]}..."
