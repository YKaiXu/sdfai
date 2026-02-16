"""
Connection Manager - 通用连接管理器
管理所有类型的连接（SSH、WebSocket、HTTP等）
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ConnectionType(Enum):
    SSH = "ssh"
    WEBSOCKET = "websocket"
    HTTP = "http"
    SERIAL = "serial"
    TELNET = "telnet"


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    connection_id: str
    connection_type: ConnectionType
    host: str
    port: int
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


T = TypeVar('T')


class Connection(Generic[T]):
    """通用连接基类"""
    
    def __init__(self, info: ConnectionInfo):
        self.info = info
        self._connection: Optional[T] = None
        self._state = ConnectionState.DISCONNECTED
        self._on_connect_callbacks: list = []
        self._on_disconnect_callbacks: list = []
        self._on_error_callbacks: list = []
    
    @property
    def state(self) -> ConnectionState:
        return self._state
    
    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED
    
    async def connect(self) -> bool:
        raise NotImplementedError
    
    async def disconnect(self) -> bool:
        raise NotImplementedError
    
    async def send(self, data: Any) -> bool:
        raise NotImplementedError
    
    async def receive(self) -> Any:
        raise NotImplementedError
    
    def on_connect(self, callback: Callable):
        self._on_connect_callbacks.append(callback)
    
    def on_disconnect(self, callback: Callable):
        self._on_disconnect_callbacks.append(callback)
    
    def on_error(self, callback: Callable):
        self._on_error_callbacks.append(callback)
    
    async def _notify_connect(self):
        for callback in self._on_connect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except:
                pass
    
    async def _notify_disconnect(self):
        for callback in self._on_disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except:
                pass
    
    async def _notify_error(self, error: str):
        for callback in self._on_error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self, error)
                else:
                    callback(self, error)
            except:
                pass


class ConnectionManager:
    """连接管理器 - 管理所有连接"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._connections: Dict[str, Connection] = {}
        self._state_file = data_dir / "connections.json"
        self._load_state()
    
    def register(self, connection: Connection) -> str:
        conn_id = connection.info.connection_id
        self._connections[conn_id] = connection
        self._save_state()
        return conn_id
    
    def unregister(self, connection_id: str) -> bool:
        if connection_id in self._connections:
            del self._connections[connection_id]
            self._save_state()
            return True
        return False
    
    def get(self, connection_id: str) -> Optional[Connection]:
        return self._connections.get(connection_id)
    
    def get_by_type(self, conn_type: ConnectionType) -> list:
        return [
            conn for conn in self._connections.values()
            if conn.info.connection_type == conn_type
        ]
    
    def get_all(self) -> Dict[str, Connection]:
        return self._connections.copy()
    
    async def connect_all(self) -> Dict[str, bool]:
        results = {}
        for conn_id, conn in self._connections.items():
            try:
                results[conn_id] = await conn.connect()
            except Exception as e:
                results[conn_id] = False
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        results = {}
        for conn_id, conn in self._connections.items():
            try:
                results[conn_id] = await conn.disconnect()
            except:
                results[conn_id] = False
        return results
    
    def list_connections(self) -> list:
        return [
            {
                "id": conn.info.connection_id,
                "type": conn.info.connection_type.value,
                "host": conn.info.host,
                "port": conn.info.port,
                "state": conn.state.value,
                "connected_at": conn.info.connected_at.isoformat() if conn.info.connected_at else None
            }
            for conn in self._connections.values()
        ]
    
    def _save_state(self):
        state = {
            "connections": self.list_connections(),
            "updated_at": datetime.now().isoformat()
        }
        self._state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def _load_state(self):
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding='utf-8'))
            except:
                pass
