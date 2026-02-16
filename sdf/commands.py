"""
SDF Commands - SDF.org命令系统
包含命令翻译器，将自然语言翻译为SDF命令
扩展匹配模式，支持更多自然语言表达
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CommandType(Enum):
    COM = "com"
    ROOM = "room"
    PRIVATE = "private"
    SHELL = "shell"
    SYSTEM = "system"


@dataclass
class SDFCommand:
    command_type: CommandType
    raw_input: str
    translated: str
    target: Optional[str] = None
    args: List[str] = field(default_factory=list)
    needs_confirmation: bool = False
    description: str = ""


SDF_COMMANDS = {
    "com": {"help": "Enter COM chat system", "usage": "com"},
    "g": {"help": "Go to room", "usage": "g <room>"},
    "s": {"help": "Send private message", "usage": "s <user> <message>"},
    "w": {"help": "Who is online", "usage": "w"},
    "q": {"help": "Quit COM", "usage": "q"},
    "h": {"help": "Help", "usage": "h"},
    "i": {"help": "Show room info", "usage": "i"},
    "l": {"help": "List rooms", "usage": "l"},
}

LINUX_COMMANDS = {
    "ls": {"help": "List files", "dangerous": False},
    "cd": {"help": "Change directory", "dangerous": False},
    "pwd": {"help": "Print working directory", "dangerous": False},
    "cat": {"help": "Display file contents", "dangerous": False},
    "less": {"help": "View file with pager", "dangerous": False},
    "head": {"help": "Show first lines", "dangerous": False},
    "tail": {"help": "Show last lines", "dangerous": False},
    "grep": {"help": "Search text", "dangerous": False},
    "find": {"help": "Find files", "dangerous": False},
    "whoami": {"help": "Show current user", "dangerous": False},
    "date": {"help": "Show date/time", "dangerous": False},
    "uptime": {"help": "Show system uptime", "dangerous": False},
    "df": {"help": "Disk free space", "dangerous": False},
    "du": {"help": "Disk usage", "dangerous": False},
    "ps": {"help": "Process status", "dangerous": False},
    "top": {"help": "Process monitor", "dangerous": False},
    "rm": {"help": "Remove files", "dangerous": True},
    "mv": {"help": "Move/rename files", "dangerous": True},
    "cp": {"help": "Copy files", "dangerous": False},
    "chmod": {"help": "Change permissions", "dangerous": True},
    "chown": {"help": "Change owner", "dangerous": True},
    "kill": {"help": "Kill process", "dangerous": True},
}

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r">\s*/dev/",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",
]


class CommandTranslator:
    NATURAL_LANGUAGE_PATTERNS = [
        (r"切换到(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"去(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"进入(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"换到(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"跳转到?(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"转到(.+)(房间|聊天室|频道)", "g {room}", "room"),
        (r"私聊(.+?)(说|发|，|,)\s*(.+)", "s {user} {message}", "private"),
        (r"给(.+?)(发|发送|说|，|,)\s*(.+)", "s {user} {message}", "private"),
        (r"告诉(.+?)(.+)", "s {user} {message}", "private"),
        (r"私信(.+?)(.+)", "s {user} {message}", "private"),
        (r"悄悄话(.+?)(.+)", "s {user} {message}", "private"),
        (r"发送(.+?)到com", "com: {message}", "com"),
        (r"在com(里?|中?)(说|发|发送)\s*(.+)", "com: {message}", "com"),
        (r"com(里?|中?)(说|发|发送)\s*(.+)", "com: {message}", "com"),
        (r"群发(.+)", "com: {message}", "com"),
        (r"查看在线用户", "w", "com"),
        (r"谁在线", "w", "com"),
        (r"在线用户", "w", "com"),
        (r"列出房间", "l", "com"),
        (r"查看房间", "l", "com"),
        (r"房间列表", "l", "com"),
        (r"退出聊天", "q", "com"),
        (r"离开聊天", "q", "com"),
        (r"退出com", "q", "com"),
        (r"帮助", "h", "com"),
        (r"帮助信息", "h", "com"),
        (r"执行(.+?)命令", "sh: {command}", "shell"),
        (r"运行(.+)", "sh: {command}", "shell"),
        (r"跑(.+)", "sh: {command}", "shell"),
        (r"执行(.+)", "sh: {command}", "shell"),
    ]
    
    def __init__(self):
        self.command_history: List[SDFCommand] = []
    
    def translate(self, natural_input: str) -> SDFCommand:
        natural_input = natural_input.strip()
        
        for pattern, template, cmd_type in self.NATURAL_LANGUAGE_PATTERNS:
            match = re.search(pattern, natural_input)
            if match:
                return self._build_from_template(
                    natural_input, 
                    template, 
                    cmd_type, 
                    match.groups()
                )
        
        return SDFCommand(
            command_type=CommandType.SHELL,
            raw_input=natural_input,
            translated=natural_input,
            description="Direct shell command"
        )
    
    def _build_from_template(
        self, 
        raw: str, 
        template: str, 
        cmd_type: str,
        groups: Tuple
    ) -> SDFCommand:
        if cmd_type == "room":
            room = groups[0].strip() if groups else ""
            return SDFCommand(
                command_type=CommandType.ROOM,
                raw_input=raw,
                translated=f"g {room}",
                target=room,
                description=f"Switch to room: {room}"
            )
        elif cmd_type == "private":
            user = groups[0].strip() if len(groups) > 0 else ""
            message = groups[2].strip() if len(groups) > 2 else (groups[1].strip() if len(groups) > 1 else "")
            return SDFCommand(
                command_type=CommandType.PRIVATE,
                raw_input=raw,
                translated=f"s {user} {message}",
                target=user,
                args=[message],
                description=f"Private message to {user}"
            )
        elif cmd_type == "com":
            message = groups[0].strip() if groups else ""
            return SDFCommand(
                command_type=CommandType.COM,
                raw_input=raw,
                translated=f"com: {message}",
                args=[message],
                description=f"COM message: {message}"
            )
        elif cmd_type == "shell":
            command = groups[0].strip() if groups else ""
            return SDFCommand(
                command_type=CommandType.SHELL,
                raw_input=raw,
                translated=f"sh: {command}",
                args=[command],
                description=f"Shell command: {command}",
                needs_confirmation=self.is_dangerous(command)
            )
        
        return SDFCommand(
            command_type=CommandType.SHELL,
            raw_input=raw,
            translated=raw
        )
    
    def is_dangerous(self, command: str) -> bool:
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return True
        
        cmd_parts = command.split()
        if cmd_parts:
            base_cmd = cmd_parts[0]
            if base_cmd in LINUX_COMMANDS:
                return LINUX_COMMANDS[base_cmd].get("dangerous", False)
        
        return False
    
    def needs_confirmation(self, command: str) -> bool:
        return self.is_dangerous(command)
    
    def get_command_help(self, command: str) -> str:
        cmd_parts = command.split()
        if not cmd_parts:
            return ""
        
        base_cmd = cmd_parts[0]
        
        if base_cmd in SDF_COMMANDS:
            return SDF_COMMANDS[base_cmd]["help"]
        
        if base_cmd in LINUX_COMMANDS:
            return LINUX_COMMANDS[base_cmd]["help"]
        
        return ""
    
    def list_sdf_commands(self) -> Dict[str, Dict]:
        return SDF_COMMANDS.copy()
    
    def list_linux_commands(self) -> Dict[str, Dict]:
        return LINUX_COMMANDS.copy()
    
    def add_to_history(self, command: SDFCommand):
        self.command_history.append(command)
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]
    
    def get_history(self, limit: int = 20) -> List[SDFCommand]:
        return self.command_history[-limit:]


class SDFCommands:
    def __init__(self, translator: CommandTranslator = None):
        self.translator = translator or CommandTranslator()
    
    def parse(self, input_str: str) -> SDFCommand:
        return self.translator.translate(input_str)
    
    def execute_with_confirmation(
        self, 
        command: SDFCommand, 
        confirm_callback=None
    ) -> str:
        if command.needs_confirmation or self.translator.needs_confirmation(command.translated):
            if confirm_callback:
                if not confirm_callback(command):
                    return "Command cancelled by user"
        
        return command.translated
    
    def get_help_text(self) -> str:
        help_text = "SDF COM Commands:\n"
        for cmd, info in SDF_COMMANDS.items():
            help_text += f"  {cmd:<10} - {info['help']}\n"
        
        help_text += "\nCommon Linux Commands:\n"
        for cmd, info in list(LINUX_COMMANDS.items())[:10]:
            dangerous = " [!]" if info.get("dangerous") else ""
            help_text += f"  {cmd:<10} - {info['help']}{dangerous}\n"
        
        return help_text
