"""
SDF Connection - SDF.org连接管理
AsyncSSH持久连接，自动重连，房间记忆
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass

try:
    import asyncssh
except ImportError:
    asyncssh = None


@dataclass
class ConnectionConfig:
    host: str = "sdf.org"
    port: int = 22
    username: str = ""
    password: str = ""
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    idle_timeout: int = 3600
    keepalive_interval: int = 30


class SDFConnection:
    def __init__(self, config: ConnectionConfig, data_dir: Path):
        self.config = config
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._conn = None
        self._connected = False
        self._connecting = False
        self._last_activity = datetime.now()
        self._on_disconnect: Optional[Callable] = None
        self._on_reconnect: Optional[Callable] = None
        self._reconnect_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        if self._connecting:
            return False
        
        self._connecting = True
        
        try:
            if not asyncssh:
                raise RuntimeError("asyncssh not installed")
            
            self._conn = await asyncssh.connect(
                self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                known_hosts=None,
                keepalive_interval=self.config.keepalive_interval
            )
            
            self._connected = True
            self._last_activity = datetime.now()
            self._save_connection_state(True)
            
            self._start_idle_monitor()
            
            return True
            
        except Exception as e:
            self._save_connection_state(False, str(e))
            return False
        finally:
            self._connecting = False
    
    async def disconnect(self) -> bool:
        self._stop_reconnect()
        
        if self._conn:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except:
                pass
        
        self._connected = False
        self._conn = None
        self._save_connection_state(False)
        return True
    
    async def reconnect(self) -> bool:
        await self.disconnect()
        await asyncio.sleep(self.config.reconnect_delay)
        
        success = await self.connect()
        
        if success and self._on_reconnect:
            await self._on_reconnect()
        
        return success
    
    def _start_idle_monitor(self):
        asyncio.create_task(self._monitor_idle())
    
    async def _monitor_idle(self):
        while self._connected:
            await asyncio.sleep(60)
            
            idle_time = (datetime.now() - self._last_activity).total_seconds()
            
            if idle_time > self.config.idle_timeout:
                await self.disconnect()
                if self._on_disconnect:
                    await self._on_disconnect()
                break
    
    def _stop_reconnect(self):
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
    
    def start_auto_reconnect(self, on_reconnect: Callable = None):
        self._on_reconnect = on_reconnect
        self._reconnect_task = asyncio.create_task(self._auto_reconnect_loop())
    
    async def _auto_reconnect_loop(self):
        while self.config.auto_reconnect:
            await asyncio.sleep(self.config.reconnect_delay)
            
            if not self._connected and not self._connecting:
                await self.reconnect()
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def idle_seconds(self) -> float:
        return (datetime.now() - self._last_activity).total_seconds()
    
    def update_activity(self):
        self._last_activity = datetime.now()
    
    def on_disconnect(self, callback: Callable):
        self._on_disconnect = callback
    
    def on_reconnect(self, callback: Callable):
        self._on_reconnect = callback
    
    def _get_state_file(self) -> Path:
        return self.data_dir / "connection_state.json"
    
    def _save_connection_state(self, connected: bool, error: str = None):
        state = {
            "connected": connected,
            "timestamp": datetime.now().isoformat(),
            "host": self.config.host,
            "username": self.config.username
        }
        if error:
            state["error"] = error
        
        state_file = self._get_state_file()
        state_file.write_text(
            __import__('json').dumps(state, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    async def execute(self, command: str, timeout: int = 30) -> str:
        if not self._connected:
            return "Not connected"
        
        try:
            result = await asyncio.wait_for(
                self._conn.run(command, check=False),
                timeout=timeout
            )
            self._last_activity = datetime.now()
            return result.stdout
        except asyncio.TimeoutError:
            return f"Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"
    
    async def open_session(self):
        if not self._connected:
            return None, None
        
        try:
            writer, reader = await self._conn.open_session(
                term_type='xterm',
                encoding='utf-8'
            )
            self._last_activity = datetime.now()
            return writer, reader
        except Exception as e:
            return None, None
