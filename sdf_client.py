#!/usr/bin/env python3
"""
SDF.org COM Chat Client for SDFAI
Uses connection_manager (AsyncSSH) for all connections.
SECURITY: All connections go through connection_manager module.
"""
import asyncio
import logging
import time
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from enum import Enum

from connection_manager import (
    COMChatConnection,
    ConnectionConfig,
    CommandResult,
    create_sdf_com_connection
)

logger = logging.getLogger(__name__)


class SDFConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    IN_COM = "in_com"


@dataclass
class COMMessage:
    sender: str
    content: str
    room: str = "lobby"
    timestamp: float = field(default_factory=time.time)
    raw: str = ""


class SDFClient:
    """
    SDF.org SSH client with COM chat support.
    Uses AsyncSSH via connection_manager for all connections.
    """
    
    def __init__(self, host: str = "sdf.org", port: int = 22):
        self.host = host
        self.port = port
        self._connection: Optional[COMChatConnection] = None
        self.state = SDFConnectionState.DISCONNECTED
        self._username: str = ""
    
    async def connect(self, username: str, password: str) -> bool:
        if self.state != SDFConnectionState.DISCONNECTED:
            return True
        
        logger.info(f"Connecting to {self.host}...")
        self.state = SDFConnectionState.CONNECTING
        
        try:
            self._connection = await create_sdf_com_connection(
                host=self.host,
                port=self.port,
                username=username,
                password=password
            )
            
            if await self._connection.connect():
                self._username = username
                self.state = SDFConnectionState.CONNECTED
                logger.info("SSH connection established")
                return True
            else:
                self.state = SDFConnectionState.DISCONNECTED
                return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.state = SDFConnectionState.DISCONNECTED
            return False
    
    async def enter_com(self, room: str = "lobby") -> bool:
        if self.state != SDFConnectionState.CONNECTED:
            logger.warning("Not connected to SDF")
            return False
        
        logger.info(f"Entering COM room: {room}")
        
        if await self._connection.enter_com(room):
            self.state = SDFConnectionState.IN_COM
            logger.info("Entered COM successfully")
            return True
        else:
            logger.warning("Failed to enter COM")
            return False
    
    async def exit_com(self) -> bool:
        if self.state != SDFConnectionState.IN_COM:
            return True
        
        logger.info("Exiting COM")
        
        if await self._connection.exit_com():
            self.state = SDFConnectionState.CONNECTED
            return True
        return False
    
    async def switch_room(self, room: str) -> bool:
        if self.state != SDFConnectionState.IN_COM:
            logger.warning("Not in COM chat room")
            return False
        
        logger.info(f"Switching to room: {room}")
        return await self._connection.switch_room(room)
    
    async def send_message(self, message: str) -> bool:
        if self.state != SDFConnectionState.IN_COM:
            logger.warning("Not in COM chat room")
            return False
        
        return await self._connection.send_message(message)
    
    async def send_private_message(self, user: str, message: str) -> bool:
        if self.state != SDFConnectionState.IN_COM:
            logger.warning("Not in COM chat room")
            return False
        
        logger.info(f"Sending private message to {user}")
        return await self._connection.send_private_message(user, message)
    
    async def get_online_users(self) -> CommandResult:
        return await self._connection.get_online_users()
    
    async def list_rooms(self) -> CommandResult:
        return await self._connection.list_rooms()
    
    def set_message_callback(self, callback: Callable):
        if self._connection:
            self._connection.set_message_callback(callback)
    
    async def start_monitor(self):
        if self._connection:
            await self._connection.start_monitor()
        logger.info("COM monitor started")
    
    async def stop_monitor(self):
        if self._connection:
            await self._connection.stop_monitor()
        logger.info("COM monitor stopped")
    
    async def disconnect(self):
        if self.state == SDFConnectionState.IN_COM:
            await self.exit_com()
        
        if self._connection:
            await self._connection.disconnect()
        
        self.state = SDFConnectionState.DISCONNECTED
        logger.info("Disconnected from SDF")
    
    def get_screen_text(self) -> str:
        if self._connection:
            return self._connection.get_screen_text()
        return ""
    
    @property
    def current_room(self) -> str:
        if self._connection:
            return self._connection.current_room
        return "lobby"


class SDFCOMIntegration:
    """Integration class for SDFAI"""
    
    def __init__(self, config: dict, message_handler: Callable):
        self.config = config
        self.message_handler = message_handler
        self.client: Optional[SDFClient] = None
    
    async def start(self) -> bool:
        sdf_config = self.config.get("sdf", {})
        
        if not sdf_config.get("enabled"):
            logger.info("SDF integration disabled")
            return False
        
        host = sdf_config.get("host", "sdf.org")
        port = sdf_config.get("port", 22)
        username = sdf_config.get("username", "")
        password = sdf_config.get("password", "")
        room = sdf_config.get("room", "lobby")
        
        if not username or not password:
            logger.error("SDF credentials not configured")
            return False
        
        self.client = SDFClient(host, port)
        
        if not await self.client.connect(username, password):
            return False
        
        if not await self.client.enter_com(room):
            await self.client.disconnect()
            return False
        
        integration_self = self
        
        async def on_com_message(msg: Dict):
            com_msg = COMMessage(
                sender=msg.get("sender", ""),
                content=msg.get("content", ""),
                room=msg.get("room", "lobby"),
                timestamp=msg.get("timestamp", time.time()),
                raw=msg.get("raw", "")
            )
            await integration_self.message_handler(com_msg)
        
        self.client.set_message_callback(on_com_message)
        await self.client.start_monitor()
        
        logger.info("SDF COM integration started")
        return True
    
    async def stop(self):
        if self.client:
            await self.client.stop_monitor()
            await self.client.disconnect()
    
    async def send_message(self, message: str) -> bool:
        if self.client:
            return await self.client.send_message(message)
        return False
    
    async def send_private_message(self, user: str, message: str) -> bool:
        if self.client:
            return await self.client.send_private_message(user, message)
        return False
    
    async def switch_room(self, room: str) -> bool:
        if self.client:
            return await self.client.switch_room(room)
        return False
    
    def get_current_room(self) -> str:
        if self.client:
            return self.client.current_room
        return ""


if __name__ == "__main__":
    async def test():
        client = SDFClient()
        
        async def on_message(msg: COMMessage):
            print(f"[{msg.sender}] {msg.content}")
        
        if await client.connect("yupeng", "ykx130729"):
            print("Connected!")
            
            if await client.enter_com():
                print("In COM!")
                
                client.set_message_callback(on_message)
                await client.start_monitor()
                
                print("Monitoring for 30 seconds...")
                await asyncio.sleep(30)
                
                await client.stop_monitor()
                await client.exit_com()
            
            await client.disconnect()
    
    asyncio.run(test())
