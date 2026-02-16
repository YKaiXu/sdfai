"""
SDF COM Channel - SDF.org COM聊天通道
使用AsyncSSH进行持久连接
"""
import asyncio
import re
from pathlib import Path
from typing import AsyncIterator, Optional
from datetime import datetime

try:
    import asyncssh
except ImportError:
    asyncssh = None

from .base import Channel, ChannelMessage, ChannelType


class SDFComChannel(Channel):
    SDF_HOST = "sdf.org"
    SDF_PORT = 22
    DEFAULT_ROOM = "lounge"
    
    HARD_CODED_PREFIXES = {
        "COM_MESSAGE": "com:",
        "SHELL_COMMAND": "sh:",
        "GO_ROOM": "g:",
        "PRIVATE_MESSAGE": "s:",
    }
    
    def __init__(self, channel_id: str, data_dir: Path, config: dict):
        super().__init__(channel_id, data_dir)
        self.config = config
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.current_room = config.get("room", self.DEFAULT_ROOM)
        self._conn = None
        self._writer = None
        self._reader = None
        self._connected = False
        self._in_com = False
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.SDFCOM
    
    async def connect(self) -> bool:
        if not asyncssh:
            return False
        
        try:
            self._conn = await asyncssh.connect(
                self.SDF_HOST,
                port=self.SDF_PORT,
                username=self.username,
                password=self.password,
                known_hosts=None
            )
            self._connected = True
            self.save_status({
                "connected": True,
                "connected_at": datetime.now().isoformat(),
                "username": self.username,
                "room": self.current_room
            })
            return True
        except Exception as e:
            self.save_status({"connected": False, "error": str(e)})
            return False
    
    async def disconnect(self) -> bool:
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
        self._connected = False
        self.save_status({"connected": False})
        return True
    
    async def enter_com(self):
        if not self._connected or self._in_com:
            return
        
        self._writer, self._reader = await self._conn.open_session(
            term_type='xterm',
            encoding='utf-8'
        )
        
        self._writer.write("com\n")
        await self._writer.drain()
        await asyncio.sleep(1)
        
        if self.current_room != self.DEFAULT_ROOM:
            self._writer.write(f"g {self.current_room}\n")
            await self._writer.drain()
            await asyncio.sleep(0.5)
        
        self._in_com = True
    
    async def send_message(self, content: str) -> bool:
        if not self._in_com:
            await self.enter_com()
        
        self._writer.write(f"{content}\n")
        await self._writer.drain()
        return True
    
    async def switch_room(self, room: str) -> bool:
        if not self._in_com:
            await self.enter_com()
        
        self._writer.write(f"g {room}\n")
        await self._writer.drain()
        self.current_room = room
        self.save_status({"room": room})
        return True
    
    async def send_private(self, user: str, message: str) -> bool:
        if not self._in_com:
            await self.enter_com()
        
        self._writer.write(f"s {user} {message}\n")
        await self._writer.drain()
        return True
    
    async def send(self, message: ChannelMessage) -> bool:
        content = message.content
        
        if content.startswith(self.HARD_CODED_PREFIXES["GO_ROOM"]):
            room = content[2:].strip()
            return await self.switch_room(room)
        elif content.startswith(self.HARD_CODED_PREFIXES["PRIVATE_MESSAGE"]):
            parts = content[2:].split(maxsplit=1)
            if len(parts) == 2:
                return await self.send_private(parts[0], parts[1])
        else:
            return await self.send_message(content)
        
        self.write_to_outbox(message)
        return True
    
    async def receive(self) -> AsyncIterator[ChannelMessage]:
        while self._running and self._in_com:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=1.0)
                if line:
                    msg = ChannelMessage(
                        channel_type=self.channel_type,
                        channel_id=self.channel_id,
                        sender="sdf",
                        content=line.strip(),
                        timestamp=datetime.now()
                    )
                    self.write_to_inbox(msg)
                    yield msg
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
    
    async def start(self):
        self._running = True
        await self.connect()
    
    async def stop(self):
        self._running = False
        await self.disconnect()
