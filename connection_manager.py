#!/usr/bin/env python3
"""
Unified Connection Manager for SDFAI
Uses AsyncSSH for all external connections - modern, secure, async-native.

SECURITY RULE: All external connections MUST use this module.
This is hardcoded to prevent LLM from using incorrect connection methods.

Connection Types:
- SDF Connection: Persistent, auto-reconnect, room memory
- Other Connections: 1-hour idle timeout with disconnect confirmation
"""
import asyncio
import logging
import re
import time
from typing import Optional, Callable, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import pyte

try:
    import asyncssh
    ASYNCSSH_AVAILABLE = True
except ImportError:
    ASYNCSSH_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    SSH_SHELL = "ssh_shell"
    SSH_COMMAND = "ssh_command"
    SFTP = "sftp"
    COM_CHAT = "com_chat"


@dataclass
class ConnectionConfig:
    host: str
    port: int = 22
    username: str = ""
    password: str = ""
    key_file: str = ""
    passphrase: str = ""
    timeout: int = 60
    terminal_type: str = "xterm"
    terminal_width: int = 120
    terminal_height: int = 40
    known_hosts: Optional[str] = None
    is_persistent: bool = False
    idle_timeout: int = 3600


@dataclass
class CommandResult:
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0


@dataclass
class ConnectionState:
    last_activity: float = field(default_factory=time.time)
    reconnect_count: int = 0
    last_room: str = "lobby"
    is_connected: bool = False
    disconnect_notified: bool = False


class AsyncSSHConnection:
    """
    AsyncSSH-based connection for all external connections.
    """
    
    _instances: Dict[str, 'AsyncSSHConnection'] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls, connection_id: str) -> Optional['AsyncSSHConnection']:
        async with cls._lock:
            return cls._instances.get(connection_id)
    
    @classmethod
    async def register_instance(cls, connection_id: str, instance: 'AsyncSSHConnection'):
        async with cls._lock:
            cls._instances[connection_id] = instance
    
    @classmethod
    async def remove_instance(cls, connection_id: str):
        async with cls._lock:
            if connection_id in cls._instances:
                del cls._instances[connection_id]
    
    def __init__(self, config: ConnectionConfig, connection_id: str = None):
        if not ASYNCSSH_AVAILABLE:
            raise RuntimeError("AsyncSSH not installed. Run: pip install asyncssh")
        
        self.config = config
        self.connection_id = connection_id or f"{config.host}:{config.port}"
        self._conn: Optional[asyncssh.SSHClientConnection] = None
        self._process: Optional[asyncssh.SSHClientProcess] = None
        self._writer: Optional[asyncssh.SSHWriter] = None
        self._reader: Optional[asyncssh.SSHReader] = None
        self._connected = False
        self._in_shell = False
        self._expect_buffer = ""
        self._screen: Optional[pyte.Screen] = None
        self._stream: Optional[pyte.Stream] = None
        self._read_lock = asyncio.Lock()
        
        self._state = ConnectionState()
        self._keepalive_task: Optional[asyncio.Task] = None
        self._idle_check_task: Optional[asyncio.Task] = None
        self._disconnect_callback: Optional[Callable] = None
        self._reconnect_callback: Optional[Callable] = None
    
    async def connect(self) -> bool:
        if self._connected:
            return True
        
        try:
            connect_kwargs = {
                "host": self.config.host,
                "port": self.config.port,
                "username": self.config.username,
                "known_hosts": None,
                "keepalive_interval": 30,
                "keepalive_count_max": 3,
            }
            
            if self.config.password:
                connect_kwargs["password"] = self.config.password
            elif self.config.key_file:
                connect_kwargs["client_keys"] = [self.config.key_file]
                if self.config.passphrase:
                    connect_kwargs["passphrase"] = self.config.passphrase
            
            self._conn = await asyncio.wait_for(
                asyncssh.connect(**connect_kwargs),
                timeout=self.config.timeout
            )
            
            self._connected = True
            self._state.is_connected = True
            self._state.last_activity = time.time()
            self._state.reconnect_count += 1
            
            await self.register_instance(self.connection_id, self)
            
            self._start_keepalive()
            if not self.config.is_persistent:
                self._start_idle_check()
            
            logger.info(f"Connected to {self.config.host}:{self.config.port}")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to {self.config.host}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        self._stop_keepalive()
        self._stop_idle_check()
        
        if self._process:
            try:
                self._process.close()
            except:
                pass
            self._process = None
        
        if self._conn:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except:
                pass
            self._conn = None
        
        self._connected = False
        self._in_shell = False
        self._state.is_connected = False
        await self.remove_instance(self.connection_id)
        logger.info(f"Disconnected from {self.config.host}")
    
    def set_disconnect_callback(self, callback: Callable):
        self._disconnect_callback = callback
    
    def set_reconnect_callback(self, callback: Callable):
        self._reconnect_callback = callback
    
    def _start_keepalive(self):
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
    
    def _stop_keepalive(self):
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
    
    def _start_idle_check(self):
        if self._idle_check_task is None or self._idle_check_task.done():
            self._idle_check_task = asyncio.create_task(self._idle_check_loop())
    
    def _stop_idle_check(self):
        if self._idle_check_task and not self._idle_check_task.done():
            self._idle_check_task.cancel()
    
    async def _keepalive_loop(self):
        while self._connected:
            try:
                await asyncio.sleep(30)
                if self._connected and self._conn:
                    # AsyncSSH没有send_ignore，使用发送空数据来保持连接
                    # 或者简单地检查连接状态
                    if hasattr(self._conn, 'is_connected') and callable(self._conn.is_connected):
                        if not self._conn.is_connected():
                            raise Exception("Connection lost")
                    logger.debug(f"Keepalive check for {self.config.host}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Keepalive failed: {e}")
                if self._connected:
                    await self._handle_disconnect()
    
    async def _idle_check_loop(self):
        while self._connected:
            try:
                await asyncio.sleep(60)
                
                idle_time = time.time() - self._state.last_activity
                
                if idle_time >= self.config.idle_timeout:
                    if not self._state.disconnect_notified:
                        self._state.disconnect_notified = True
                        if self._disconnect_callback:
                            await self._disconnect_callback(self.connection_id, idle_time)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Idle check error: {e}")
    
    async def _handle_disconnect(self):
        logger.warning(f"Connection lost to {self.config.host}")
        
        was_in_shell = self._in_shell
        self._connected = False
        self._in_shell = False
        self._state.is_connected = False
        
        if self.config.is_persistent and self._reconnect_callback:
            logger.info(f"Attempting auto-reconnect to {self.config.host}")
            await self._reconnect_callback(self.connection_id)
    
    def update_activity(self):
        self._state.last_activity = time.time()
        self._state.disconnect_notified = False
    
    async def invoke_shell(self) -> bool:
        if not self._connected:
            logger.error("Not connected")
            return False
        
        try:
            self._process = await self._conn.create_process(
                term_type=self.config.terminal_type,
                term_size=(self.config.terminal_height, self.config.terminal_width)
            )
            
            self._writer = self._process.stdin
            self._reader = self._process.stdout
            
            self._screen = pyte.Screen(self.config.terminal_width, self.config.terminal_height)
            self._stream = pyte.Stream(self._screen)
            
            await asyncio.sleep(0.5)
            await self._read_output(0.5)
            
            self._in_shell = True
            self.update_activity()
            logger.info("Shell invoked")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invoke shell: {e}")
            return False
    
    async def _read_output(self, timeout: float = 1.0) -> str:
        async with self._read_lock:
            if not self._reader:
                return ""
            
            output = ""
            
            try:
                while True:
                    try:
                        data = await asyncio.wait_for(
                            self._reader.read(4096),
                            timeout=0.1
                        )
                        if not data:
                            break
                        decoded = data if isinstance(data, str) else data.decode('utf-8', errors='ignore')
                        output += decoded
                        self._expect_buffer += decoded
                        if self._stream:
                            self._stream.feed(decoded)
                    except asyncio.TimeoutError:
                        break
            except Exception as e:
                logger.debug(f"Read error: {e}")
            
            if output:
                self.update_activity()
            
            return output
    
    async def expect(self, pattern: str, timeout: float = 10.0) -> bool:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            await self._read_output(0.1)
            
            if re.search(pattern, self._expect_buffer, re.IGNORECASE | re.MULTILINE):
                return True
        
        return False
    
    async def send(self, data: str, add_newline: bool = True) -> bool:
        if not self._writer:
            return False
        
        try:
            if add_newline:
                self._writer.write(data + "\n")
            else:
                self._writer.write(data)
            await self._writer.drain()
            await asyncio.sleep(0.1)
            self.update_activity()
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False
    
    async def send_and_expect(self, command: str, expect_pattern: str,
                              timeout: float = 10.0) -> CommandResult:
        start_time = time.time()
        
        self._expect_buffer = ""
        
        if not await self.send(command):
            return CommandResult(
                success=False,
                output="",
                error="Failed to send command",
                duration=time.time() - start_time
            )
        
        found = await self.expect(expect_pattern, timeout)
        output = self._expect_buffer
        
        return CommandResult(
            success=found,
            output=output,
            error="" if found else f"Pattern not found: {expect_pattern}",
            duration=time.time() - start_time
        )
    
    async def execute_command(self, command: str, timeout: float = 30.0) -> CommandResult:
        if not self._connected:
            return CommandResult(
                success=False,
                output="",
                error="Not connected"
            )
        
        start_time = time.time()
        self.update_activity()
        
        try:
            result = await asyncio.wait_for(
                self._conn.run(command),
                timeout=timeout
            )
            
            return CommandResult(
                success=result.exit_status == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.exit_status or 0,
                duration=time.time() - start_time
            )
        except asyncio.TimeoutError:
            return CommandResult(
                success=False,
                output="",
                error="Command timeout",
                duration=time.time() - start_time
            )
        except Exception as e:
            return CommandResult(
                success=False,
                output="",
                error=str(e),
                duration=time.time() - start_time
            )
    
    def get_screen_text(self) -> str:
        if not self._screen:
            return ""
        
        lines = []
        for y in range(self._screen.lines):
            line = ""
            for x in range(self._screen.columns):
                char = self._screen.buffer[y][x]
                line += char.data
            lines.append(line.rstrip())
        
        return "\n".join(lines)
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._conn is not None
    
    @property
    def is_shell_active(self) -> bool:
        return self._in_shell and self._process is not None
    
    @property
    def idle_time(self) -> float:
        return time.time() - self._state.last_activity


class COMChatConnection(AsyncSSHConnection):
    """
    SDF COM Chat connection with persistent connection and auto-reconnect.
    Room memory: remembers last room and auto-enters on reconnect.
    """
    
    COM_PROMPT = r'[\$#>]\s*$'
    COM_MODE_PROMPT = r'COMMODE|COM>'
    
    def __init__(self, config: ConnectionConfig):
        config.is_persistent = True
        super().__init__(config, f"com:{config.host}")
        self._in_com = False
        self._message_callback: Optional[Callable] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
        
        self.set_reconnect_callback(self._auto_reconnect)
    
    async def _auto_reconnect(self, connection_id: str):
        logger.info(f"Auto-reconnecting SDF COM connection...")
        
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                if await self.connect():
                    if await self.enter_com(self._state.last_room):
                        logger.info(f"Auto-reconnect successful, in room: {self._state.last_room}")
                        return True
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt + 1} failed: {e}")
            
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        
        logger.error("Auto-reconnect failed after max retries")
        return False
    
    async def enter_com(self, room: str = "lobby") -> bool:
        if not self._connected:
            if not await self.connect():
                return False
        
        if not self._in_shell:
            if not await self.invoke_shell():
                return False
        
        result = await self.send_and_expect("com", self.COM_MODE_PROMPT, timeout=5.0)
        
        if result.success:
            self._in_com = True
            self._state.last_room = room
            logger.info(f"Entered COM mode, room: {room}")
            
            if room != "lobby":
                return await self.switch_room(room)
            
            return True
        
        logger.error("Failed to enter COM mode")
        return False
    
    async def exit_com(self) -> bool:
        if not self._in_com:
            return True
        
        await self.send("q")
        await asyncio.sleep(0.5)
        await self._read_output(0.5)
        
        self._in_com = False
        logger.info("Exited COM mode")
        return True
    
    async def switch_room(self, room: str) -> bool:
        if not self._in_com:
            logger.warning("Not in COM mode")
            return False
        
        await self.send(f"j {room}")
        await asyncio.sleep(1.5)
        await self._read_output(0.5)
        
        self._state.last_room = room
        logger.info(f"Switched to room: {room}")
        return True
    
    async def send_message(self, message: str) -> bool:
        if not self._in_com:
            logger.warning("Not in COM mode")
            return False
        
        return await self.send(message)
    
    async def send_private_message(self, user: str, message: str) -> bool:
        if not self._in_com:
            logger.warning("Not in COM mode")
            return False
        
        return await self.send(f"p {user} {message}")
    
    async def get_online_users(self) -> CommandResult:
        return await self.send_and_expect("w", self.COM_PROMPT, timeout=3.0)
    
    async def list_rooms(self) -> CommandResult:
        return await self.send_and_expect("l", self.COM_PROMPT, timeout=3.0)
    
    def set_message_callback(self, callback: Callable):
        self._message_callback = callback
    
    async def start_monitor(self):
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("COM monitor started")
    
    async def stop_monitor(self):
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("COM monitor stopped")
    
    async def _monitor_loop(self):
        seen_messages = set()
        
        while self._monitoring:
            try:
                if not self._connected or not self._in_com:
                    await asyncio.sleep(2)
                    continue
                
                await self._read_output(0.5)
                
                messages = self._parse_messages()
                for msg in messages:
                    msg_key = f"{msg.get('sender', '')}:{msg.get('content', '')[:30]}"
                    if msg_key not in seen_messages:
                        seen_messages.add(msg_key)
                        if len(seen_messages) > 100:
                            seen_messages.pop()
                        
                        if self._message_callback:
                            try:
                                if asyncio.iscoroutinefunction(self._message_callback):
                                    await self._message_callback(msg)
                                else:
                                    self._message_callback(msg)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(2)
    
    def _parse_messages(self) -> List[Dict]:
        messages = []
        screen = self.get_screen_text()
        
        for line in screen.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            patterns = [
                r'\[([^\]]+)\]\s*(.+)',
                r'<([^>]+)>\s*(.+)',
                r'([a-zA-Z0-9_@]+)\s*[:：]\s*(.+)',
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    sender = match.group(1).strip()
                    content = match.group(2).strip()
                    
                    if sender and content and sender != self.config.username:
                        if sender.upper() in ["TIP", "SYSTEM"]:
                            continue
                        if sender.lower() in ["alignment", "strength", "dexterity"]:
                            continue
                        
                        messages.append({
                            "sender": sender,
                            "content": content,
                            "room": self._state.last_room,
                            "timestamp": time.time(),
                            "raw": line
                        })
                    break
        
        return messages
    
    @property
    def current_room(self) -> str:
        return self._state.last_room


class ConnectionManager:
    """
    Centralized connection manager.
    All connections MUST be created through this manager.
    """
    
    _instance: Optional['ConnectionManager'] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> 'ConnectionManager':
        async with cls._lock:
            if cls._instance is None:
                cls._instance = ConnectionManager()
            return cls._instance
    
    def __init__(self):
        self._connections: Dict[str, AsyncSSHConnection] = {}
        self._com_connections: Dict[str, COMChatConnection] = {}
        self._disconnect_notification_callback: Optional[Callable] = None
    
    def set_disconnect_notification_callback(self, callback: Callable):
        self._disconnect_notification_callback = callback
    
    async def create_ssh_connection(self, config: ConnectionConfig,
                                    connection_id: str = None) -> AsyncSSHConnection:
        conn_id = connection_id or f"ssh:{config.host}:{config.port}"
        
        if conn_id in self._connections:
            return self._connections[conn_id]
        
        conn = AsyncSSHConnection(config, conn_id)
        
        if not config.is_persistent:
            async def on_idle_disconnect(conn_id: str, idle_time: float):
                if self._disconnect_notification_callback:
                    await self._disconnect_notification_callback(conn_id, idle_time)
            
            conn.set_disconnect_callback(on_idle_disconnect)
        
        self._connections[conn_id] = conn
        return conn
    
    async def create_com_connection(self, config: ConnectionConfig) -> COMChatConnection:
        conn_id = f"com:{config.host}"
        
        if conn_id in self._com_connections:
            return self._com_connections[conn_id]
        
        conn = COMChatConnection(config)
        self._com_connections[conn_id] = conn
        return conn
    
    def get_connection(self, connection_id: str) -> Optional[AsyncSSHConnection]:
        return self._connections.get(connection_id) or self._com_connections.get(connection_id)
    
    def get_com_connection(self, host: str = "sdf.org") -> Optional[COMChatConnection]:
        return self._com_connections.get(f"com:{host}")
    
    async def close_all(self):
        for conn in list(self._connections.values()):
            await conn.disconnect()
        self._connections.clear()
        
        for conn in list(self._com_connections.values()):
            await conn.stop_monitor()
            await conn.disconnect()
        self._com_connections.clear()
        
        logger.info("All connections closed")


async def create_sdf_com_connection(host: str = "sdf.org", port: int = 22,
                                    username: str = "", password: str = "") -> COMChatConnection:
    """
    Factory function to create SDF COM connection.
    This is the ONLY way to create COM connections.
    
    SECURITY: This function is hardcoded to use AsyncSSH.
    Do not modify to use other connection methods.
    """
    config = ConnectionConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        is_persistent=True
    )
    
    manager = await ConnectionManager.get_instance()
    return await manager.create_com_connection(config)


if __name__ == "__main__":
    async def test():
        conn = await create_sdf_com_connection(
            host="sdf.org",
            username="yupeng",
            password="ykx130729"
        )
        
        if await conn.connect():
            print("Connected!")
            
            if await conn.enter_com():
                print("In COM!")
                
                result = await conn.get_online_users()
                print(f"Online users: {result.output[:200]}")
                
                await conn.exit_com()
            
            await conn.disconnect()
    
    asyncio.run(test())
