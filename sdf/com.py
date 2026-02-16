"""
SDF COM - SDF.org COM聊天核心模块
这是sdf模块的核心，不依赖任何特定连接方式
"""
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable, AsyncIterator
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class COMState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    IN_COM = "in_com"


@dataclass
class COMConfig:
    default_room: str = "lounge"
    message_timeout: float = 30.0
    reconnect_attempts: int = 3
    idle_timeout: int = 3600


@dataclass
class COMMessage:
    sender: str
    content: str
    room: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_private: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


HARDCODED_PREFIXES = {
    "COM_MESSAGE": "com:",
    "SHELL_COMMAND": "sh:",
    "GO_ROOM": "g:",
    "PRIVATE_MESSAGE": "s:",
}


class COMClient:
    """
    COM聊天客户端核心
    不依赖特定连接方式，通过回调函数与外部连接交互
    """
    
    def __init__(
        self, 
        config: COMConfig,
        data_dir: Path,
        send_callback: Callable[[str], Any] = None,
        receive_callback: Callable[[], AsyncIterator[str]] = None
    ):
        self.config = config
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._send_callback = send_callback
        self._receive_callback = receive_callback
        self._state = COMState.DISCONNECTED
        self._current_room = config.default_room
        self._last_activity = datetime.now()
        self._message_handlers: list = []
    
    def set_send_callback(self, callback: Callable[[str], Any]):
        self._send_callback = callback
    
    def set_receive_callback(self, callback: Callable[[], AsyncIterator[str]]):
        self._receive_callback = callback
    
    @property
    def state(self) -> COMState:
        return self._state
    
    @property
    def current_room(self) -> str:
        return self._current_room
    
    @property
    def is_in_com(self) -> bool:
        return self._state == COMState.IN_COM
    
    async def enter_com(self) -> bool:
        if self._state == COMState.IN_COM:
            return True
        
        if not self._send_callback:
            return False
        
        try:
            await self._send("com")
            await asyncio.sleep(1)
            
            if self._current_room != self.config.default_room:
                await self._send(f"g {self._current_room}")
            
            self._state = COMState.IN_COM
            self._last_activity = datetime.now()
            self._save_state()
            return True
        except:
            return False
    
    async def exit_com(self) -> bool:
        if self._state != COMState.IN_COM:
            return True
        
        try:
            await self._send("q")
            self._state = COMState.CONNECTED
            self._save_state()
            return True
        except:
            return False
    
    async def send_message(self, message: str) -> bool:
        if self._state != COMState.IN_COM:
            if not await self.enter_com():
                return False
        
        try:
            await self._send(message)
            self._last_activity = datetime.now()
            self._log_message(COMMessage(
                sender="me",
                content=message,
                room=self._current_room
            ))
            return True
        except:
            return False
    
    async def switch_room(self, room: str) -> bool:
        if self._state != COMState.IN_COM:
            if not await self.enter_com():
                return False
        
        try:
            await self._send(f"g {room}")
            self._current_room = room
            self._last_activity = datetime.now()
            self._save_state()
            return True
        except:
            return False
    
    async def send_private(self, user: str, message: str) -> bool:
        if self._state != COMState.IN_COM:
            if not await self.enter_com():
                return False
        
        try:
            await self._send(f"s {user} {message}")
            self._last_activity = datetime.now()
            self._log_message(COMMessage(
                sender="me",
                content=message,
                room=self._current_room,
                is_private=True,
                metadata={"to": user}
            ))
            return True
        except:
            return False
    
    async def who_online(self) -> bool:
        return await self._com_command("w")
    
    async def list_rooms(self) -> bool:
        return await self._com_command("l")
    
    async def show_help(self) -> bool:
        return await self._com_command("h")
    
    async def _com_command(self, cmd: str) -> bool:
        if self._state != COMState.IN_COM:
            if not await self.enter_com():
                return False
        
        try:
            await self._send(cmd)
            self._last_activity = datetime.now()
            return True
        except:
            return False
    
    async def _send(self, message: str) -> None:
        if self._send_callback:
            if asyncio.iscoroutinefunction(self._send_callback):
                await self._send_callback(message)
            else:
                self._send_callback(message)
    
    def on_state_change(self, new_state: COMState):
        self._state = new_state
        self._save_state()
    
    def on_connected(self):
        self._state = COMState.CONNECTED
        self._last_activity = datetime.now()
        self._save_state()
    
    def on_disconnected(self):
        self._state = COMState.DISCONNECTED
        self._save_state()
    
    def add_message_handler(self, handler: Callable[[COMMessage], Any]):
        self._message_handlers.append(handler)
    
    def _log_message(self, message: COMMessage):
        log_file = self.data_dir / "messages.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sender": message.sender,
                "content": message.content,
                "room": message.room,
                "timestamp": message.timestamp.isoformat(),
                "is_private": message.is_private
            }, ensure_ascii=False) + '\n')
    
    def _save_state(self):
        state_file = self.data_dir / "com_state.json"
        state_file.write_text(json.dumps({
            "state": self._state.value,
            "current_room": self._current_room,
            "last_activity": self._last_activity.isoformat()
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def _load_state(self) -> Dict:
        state_file = self.data_dir / "com_state.json"
        if state_file.exists():
            try:
                return json.loads(state_file.read_text(encoding='utf-8'))
            except:
                pass
        return {}
