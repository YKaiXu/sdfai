"""
Feishu Channel - 飞书通讯通道
"""
import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Optional
from datetime import datetime

from .base import Channel, ChannelMessage, ChannelType


class FeishuChannel(Channel):
    def __init__(self, channel_id: str, data_dir: Path, config: dict):
        super().__init__(channel_id, data_dir)
        self.config = config
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self._ws = None
        self._connected = False
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.FEISHU
    
    async def connect(self) -> bool:
        try:
            self._connected = True
            self.save_status({
                "connected": True,
                "connected_at": datetime.now().isoformat(),
                "app_id": self.app_id
            })
            return True
        except Exception as e:
            self.save_status({"connected": False, "error": str(e)})
            return False
    
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
    
    async def start(self):
        self._running = True
        await self.connect()
    
    async def stop(self):
        self._running = False
        await self.disconnect()
