"""
Channel Base - 通道基类
一切皆文件：每个通道都有对应的文件接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, AsyncIterator
from datetime import datetime
from pathlib import Path
import json
import asyncio


class ChannelType(Enum):
    FEISHU = "feishu"
    XUNFEI = "xunfei"
    SDFCOM = "sdfcom"
    TELEGRAM = "telegram"
    DISCORD = "discord"


@dataclass
class ChannelMessage:
    channel_type: ChannelType
    channel_id: str
    sender: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None
    
    def to_file(self, path: Path):
        d = {
            "channel_type": self.channel_type.value,
            "channel_id": self.channel_id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reply_to": self.reply_to
        }
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    
    @classmethod
    def from_file(cls, path: Path) -> 'ChannelMessage':
        d = json.loads(path.read_text(encoding='utf-8'))
        return cls(
            channel_type=ChannelType(d["channel_type"]),
            channel_id=d["channel_id"],
            sender=d["sender"],
            content=d["content"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            metadata=d.get("metadata", {}),
            reply_to=d.get("reply_to")
        )


class Channel(ABC):
    def __init__(self, channel_id: str, data_dir: Path):
        self.channel_id = channel_id
        self.data_dir = data_dir / channel_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir = self.data_dir / "inbox"
        self.outbox_dir = self.data_dir / "outbox"
        self.inbox_dir.mkdir(exist_ok=True)
        self.outbox_dir.mkdir(exist_ok=True)
        self._running = False
    
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        pass
    
    @abstractmethod
    async def send(self, message: ChannelMessage) -> bool:
        pass
    
    @abstractmethod
    async def receive(self) -> AsyncIterator[ChannelMessage]:
        pass
    
    def write_to_inbox(self, message: ChannelMessage):
        filename = f"{message.timestamp.strftime('%Y%m%d_%H%M%S')}_{message.sender}.json"
        message.to_file(self.inbox_dir / filename)
    
    def write_to_outbox(self, message: ChannelMessage):
        filename = f"{message.timestamp.strftime('%Y%m%d_%H%M%S')}_{message.channel_type.value}.json"
        message.to_file(self.outbox_dir / filename)
    
    def read_pending_outbox(self) -> list:
        messages = []
        for f in self.outbox_dir.glob("*.json"):
            try:
                messages.append(ChannelMessage.from_file(f))
            except:
                pass
        return messages
    
    def get_status_file(self) -> Path:
        return self.data_dir / "status.json"
    
    def save_status(self, status: Dict[str, Any]):
        status_file = self.get_status_file()
        status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def load_status(self) -> Dict[str, Any]:
        status_file = self.get_status_file()
        if status_file.exists():
            return json.loads(status_file.read_text(encoding='utf-8'))
        return {}
