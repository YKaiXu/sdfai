"""
SDFAI Message Router - 消息路由器
硬编码命令前缀，防止LLM修改
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum


class CommandPrefix:
    COM_MESSAGE = "com:"
    SHELL_COMMAND = "sh:"
    GO_ROOM = "g:"
    PRIVATE_MESSAGE = "s:"


class RouteType(Enum):
    COM_MESSAGE = "com_message"
    SHELL_COMMAND = "shell_command"
    GO_ROOM = "go_room"
    PRIVATE_MESSAGE = "private_message"
    UNKNOWN = "unknown"


@dataclass
class RoutedMessage:
    route_type: RouteType
    prefix: str
    content: str
    target: Optional[str] = None
    original: str = ""


class MessageRouter:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.handlers: Dict[RouteType, Callable] = {}
    
    def register_handler(self, route_type: RouteType, handler: Callable):
        self.handlers[route_type] = handler
    
    def parse_message(self, message: str) -> RoutedMessage:
        message = message.strip()
        
        if message.startswith(CommandPrefix.COM_MESSAGE):
            content = message[len(CommandPrefix.COM_MESSAGE):].strip()
            return RoutedMessage(
                route_type=RouteType.COM_MESSAGE,
                prefix=CommandPrefix.COM_MESSAGE,
                content=content,
                original=message
            )
        
        elif message.startswith(CommandPrefix.SHELL_COMMAND):
            content = message[len(CommandPrefix.SHELL_COMMAND):].strip()
            return RoutedMessage(
                route_type=RouteType.SHELL_COMMAND,
                prefix=CommandPrefix.SHELL_COMMAND,
                content=content,
                original=message
            )
        
        elif message.startswith(CommandPrefix.GO_ROOM):
            content = message[len(CommandPrefix.GO_ROOM):].strip()
            return RoutedMessage(
                route_type=RouteType.GO_ROOM,
                prefix=CommandPrefix.GO_ROOM,
                content=content,
                target=content,
                original=message
            )
        
        elif message.startswith(CommandPrefix.PRIVATE_MESSAGE):
            content = message[len(CommandPrefix.PRIVATE_MESSAGE):].strip()
            parts = content.split(maxsplit=1)
            target = parts[0] if parts else None
            msg_content = parts[1] if len(parts) > 1 else ""
            return RoutedMessage(
                route_type=RouteType.PRIVATE_MESSAGE,
                prefix=CommandPrefix.PRIVATE_MESSAGE,
                content=msg_content,
                target=target,
                original=message
            )
        
        return RoutedMessage(
            route_type=RouteType.UNKNOWN,
            prefix="",
            content=message,
            original=message
        )
    
    async def route(self, message: str) -> Optional[Any]:
        routed = self.parse_message(message)
        
        if routed.route_type in self.handlers:
            handler = self.handlers[routed.route_type]
            if asyncio.iscoroutinefunction(handler):
                return await handler(routed)
            else:
                return handler(routed)
        
        return None
    
    def get_prefix_help(self) -> str:
        return f"""
SDFAI Command Prefixes:
  {CommandPrefix.COM_MESSAGE} <message>  - Send message to COM room
  {CommandPrefix.SHELL_COMMAND} <command> - Execute shell command
  {CommandPrefix.GO_ROOM} <room>          - Switch to room
  {CommandPrefix.PRIVATE_MESSAGE} <user> <msg> - Send private message
"""
