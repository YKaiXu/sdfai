"""
SSH Connection - SSH连接实现
使用asyncssh实现SSH连接
"""
import asyncio
from pathlib import Path
from typing import Optional, Any, Callable, AsyncIterator
from datetime import datetime

try:
    import asyncssh
except ImportError:
    asyncssh = None

from .connection_manager import Connection, ConnectionInfo, ConnectionState, ConnectionType


class SSHConnectionInfo(ConnectionInfo):
    def __init__(
        self,
        connection_id: str,
        host: str,
        port: int = 22,
        username: str = "",
        password: str = "",
        **kwargs
    ):
        super().__init__(
            connection_id=connection_id,
            connection_type=ConnectionType.SSH,
            host=host,
            port=port,
            metadata={"username": username, **kwargs}
        )
        self.username = username
        self.password = password


class SSHConnection(Connection):
    """SSH连接实现"""
    
    def __init__(self, info: SSHConnectionInfo, data_dir: Path = None):
        super().__init__(info)
        self.ssh_info = info
        self.data_dir = data_dir
        self._writer = None
        self._reader = None
        self._keepalive_interval = 30
        self._idle_timeout = 3600
        self._last_activity = datetime.now()
    
    async def connect(self) -> bool:
        if not asyncssh:
            self._state = ConnectionState.ERROR
            await self._notify_error("asyncssh not installed")
            return False
        
        if self._state == ConnectionState.CONNECTED:
            return True
        
        self._state = ConnectionState.CONNECTING
        
        try:
            self._connection = await asyncssh.connect(
                self.ssh_info.host,
                port=self.ssh_info.port,
                username=self.ssh_info.username,
                password=self.ssh_info.password,
                known_hosts=None,
                keepalive_interval=self._keepalive_interval
            )
            
            self._state = ConnectionState.CONNECTED
            self.info.connected_at = datetime.now()
            self._last_activity = datetime.now()
            
            await self._notify_connect()
            return True
            
        except Exception as e:
            self._state = ConnectionState.ERROR
            self.info.error = str(e)
            await self._notify_error(str(e))
            return False
    
    async def disconnect(self) -> bool:
        if self._connection:
            try:
                self._connection.close()
                await self._connection.wait_closed()
            except:
                pass
        
        self._connection = None
        self._writer = None
        self._reader = None
        self._state = ConnectionState.DISCONNECTED
        
        await self._notify_disconnect()
        return True
    
    async def send(self, data: str) -> bool:
        if not self.is_connected:
            return False
        
        try:
            if self._writer:
                self._writer.write(f"{data}\n")
                await self._writer.drain()
                self._last_activity = datetime.now()
                return True
            return False
        except:
            return False
    
    async def receive(self) -> AsyncIterator[str]:
        if not self.is_connected or not self._reader:
            return
        
        try:
            async for line in self._reader:
                self._last_activity = datetime.now()
                yield line
        except:
            pass
    
    async def execute(self, command: str, timeout: int = 30) -> str:
        if not self.is_connected:
            return "Not connected"
        
        try:
            result = await asyncio.wait_for(
                self._connection.run(command, check=False),
                timeout=timeout
            )
            self._last_activity = datetime.now()
            return result.stdout
        except asyncio.TimeoutError:
            return f"Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"
    
    async def open_session(self) -> tuple:
        if not self.is_connected:
            return None, None
        
        try:
            self._writer, self._reader = await self._connection.open_session(
                term_type='xterm',
                encoding='utf-8'
            )
            self._last_activity = datetime.now()
            return self._writer, self._reader
        except:
            return None, None
    
    async def close_session(self) -> bool:
        if self._writer:
            try:
                self._writer.close()
            except:
                pass
        
        self._writer = None
        self._reader = None
        return True
    
    @property
    def idle_seconds(self) -> float:
        return (datetime.now() - self._last_activity).total_seconds()
    
    def update_activity(self):
        self._last_activity = datetime.now()
