"""
SDF Client - SDF.org客户端
使用AsyncSSH进行持久连接
"""
import asyncio
import re
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
from datetime import datetime
from dataclasses import dataclass, field

try:
    import asyncssh
except ImportError:
    asyncssh = None


@dataclass
class SDFConfig:
    host: str = "sdf.org"
    port: int = 22
    username: str = ""
    password: str = ""
    default_room: str = "lounge"
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    idle_timeout: int = 3600


class SDFClient:
    SDF_HOST = "sdf.org"
    SDF_PORT = 22
    DEFAULT_ROOM = "lounge"
    
    HARD_CODED_PREFIXES = {
        "COM_MESSAGE": "com:",
        "SHELL_COMMAND": "sh:",
        "GO_ROOM": "g:",
        "PRIVATE_MESSAGE": "s:",
    }
    
    def __init__(self, config: SDFConfig, data_dir: Path):
        self.config = config
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._conn = None
        self._writer = None
        self._reader = None
        self._connected = False
        self._in_com = False
        self._current_room = config.default_room
        self._last_activity = datetime.now()
    
    async def connect(self) -> bool:
        if not asyncssh:
            raise RuntimeError("asyncssh not installed")
        
        try:
            self._conn = await asyncssh.connect(
                self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                known_hosts=None
            )
            self._connected = True
            self._last_activity = datetime.now()
            return True
        except Exception as e:
            return False
    
    async def disconnect(self) -> bool:
        if self._in_com:
            await self.exit_com()
        
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
        
        self._connected = False
        return True
    
    async def enter_com(self) -> bool:
        if not self._connected or self._in_com:
            return self._in_com
        
        try:
            self._writer, self._reader = await self._conn.open_session(
                term_type='xterm',
                encoding='utf-8'
            )
            
            self._writer.write("com\n")
            await self._writer.drain()
            await asyncio.sleep(1)
            
            if self._current_room != self.DEFAULT_ROOM:
                self._writer.write(f"g {self._current_room}\n")
                await self._writer.drain()
            
            self._in_com = True
            self._last_activity = datetime.now()
            return True
        except:
            return False
    
    async def exit_com(self) -> bool:
        if not self._in_com:
            return True
        
        try:
            self._writer.write("q\n")
            await self._writer.drain()
            self._in_com = False
            return True
        except:
            self._in_com = False
            return False
    
    async def send_message(self, message: str) -> bool:
        if not self._in_com:
            if not await self.enter_com():
                return False
        
        try:
            self._writer.write(f"{message}\n")
            await self._writer.drain()
            self._last_activity = datetime.now()
            return True
        except:
            return False
    
    async def switch_room(self, room: str) -> bool:
        if not self._in_com:
            if not await self.enter_com():
                return False
        
        try:
            self._writer.write(f"g {room}\n")
            await self._writer.drain()
            self._current_room = room
            self._last_activity = datetime.now()
            return True
        except:
            return False
    
    async def send_private(self, user: str, message: str) -> bool:
        if not self._in_com:
            if not await self.enter_com():
                return False
        
        try:
            self._writer.write(f"s {user} {message}\n")
            await self._writer.drain()
            self._last_activity = datetime.now()
            return True
        except:
            return False
    
    async def execute_command(self, command: str) -> str:
        if not self._connected:
            return "Not connected"
        
        try:
            result = await self._conn.run(command, check=False)
            self._last_activity = datetime.now()
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    @property
    def current_room(self) -> str:
        return self._current_room
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_in_com(self) -> bool:
        return self._in_com
