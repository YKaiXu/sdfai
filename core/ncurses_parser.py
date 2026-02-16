"""
NCurses Parser - NCurses终端解析器
解析ncurses应用的输出，如top、htop、vim等
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ElementType(Enum):
    TEXT = "text"
    HEADER = "header"
    TABLE = "table"
    ROW = "row"
    MENU = "menu"
    STATUS = "status"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ScreenElement:
    element_type: ElementType
    content: str
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (0, 0)
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List['ScreenElement'] = field(default_factory=list)


@dataclass
class ParsedScreen:
    raw_data: str
    elements: List[ScreenElement]
    width: int = 80
    height: int = 24
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
ANSI_COLOR = re.compile(r'\x1b\[[0-9;]*m')
NCURSES_CURSOR = re.compile(r'\x1b\[[0-9]+;[0-9]+H')
NCURSES_CLEAR = re.compile(r'\x1b\[[0-9]*J')
NCURSES_ATTRS = re.compile(r'\x1b\[[0-9;]*[mHJKL]')


class NCursesParser:
    """NCurses终端输出解析器"""
    
    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self._screen_buffer: List[List[str]] = []
        self._clear_buffer()
    
    def _clear_buffer(self):
        self._screen_buffer = [[' ' for _ in range(self.width)] for _ in range(self.height)]
    
    def parse(self, data: str) -> ParsedScreen:
        self._clear_buffer()
        
        clean_data = self._strip_ansi(data)
        lines = clean_data.split('\n')
        
        elements = []
        for row, line in enumerate(lines[:self.height]):
            if line.strip():
                element = self._parse_line(line, row)
                elements.append(element)
        
        return ParsedScreen(
            raw_data=data,
            elements=elements,
            width=self.width,
            height=self.height
        )
    
    def _strip_ansi(self, data: str) -> str:
        data = ANSI_ESCAPE.sub('', data)
        data = ANSI_COLOR.sub('', data)
        data = NCURSES_CURSOR.sub('', data)
        data = NCURSES_CLEAR.sub('', data)
        return data
    
    def _parse_line(self, line: str, row: int) -> ScreenElement:
        line = line[:self.width].ljust(self.width)
        
        for col, char in enumerate(line):
            if col < self.width:
                self._screen_buffer[row][col] = char
        
        element_type = self._detect_element_type(line, row)
        
        return ScreenElement(
            element_type=element_type,
            content=line.strip(),
            position=(row, 0),
            size=(1, len(line.strip()))
        )
    
    def _detect_element_type(self, line: str, row: int) -> ElementType:
        stripped = line.strip()
        
        if not stripped:
            return ElementType.TEXT
        
        if row == 0:
            return ElementType.HEADER
        
        if re.match(r'^[\s\-\+=]+$', stripped):
            return ElementType.STATUS
        
        if re.match(r'^\s*\d+\s+', stripped):
            return ElementType.ROW
        
        if re.match(r'^\s*[\[\(][A-Za-z]', stripped):
            return ElementType.MENU
        
        if 'error' in stripped.lower() or 'fail' in stripped.lower():
            return ElementType.ERROR
        
        return ElementType.TEXT
    
    def extract_table(self, screen: ParsedScreen) -> List[Dict[str, str]]:
        rows = []
        header = None
        
        for element in screen.elements:
            if element.element_type == ElementType.HEADER:
                header = self._parse_table_row(element.content)
            elif element.element_type == ElementType.ROW:
                row_data = self._parse_table_row(element.content)
                if header and len(row_data) == len(header):
                    rows.append(dict(zip(header, row_data)))
                else:
                    rows.append({"data": element.content})
        
        return rows
    
    def _parse_table_row(self, line: str) -> List[str]:
        return [col.strip() for col in line.split() if col.strip()]
    
    def extract_menu_items(self, screen: ParsedScreen) -> List[Dict[str, str]]:
        items = []
        
        for element in screen.elements:
            if element.element_type == ElementType.MENU:
                matches = re.findall(r'\[([A-Za-z])\]\s*(\w+)', element.content)
                for key, label in matches:
                    items.append({"key": key, "label": label})
        
        return items
    
    def to_plain_text(self, screen: ParsedScreen) -> str:
        lines = []
        for element in screen.elements:
            lines.append(element.content)
        return '\n'.join(lines)


class TopParser(NCursesParser):
    """top命令输出解析器"""
    
    def parse(self, data: str) -> ParsedScreen:
        screen = super().parse(data)
        
        screen.metadata["summary"] = self._parse_summary(screen)
        screen.metadata["processes"] = self._parse_processes(screen)
        
        return screen
    
    def _parse_summary(self, screen: ParsedScreen) -> Dict:
        summary = {}
        
        for element in screen.elements[:5]:
            content = element.content
            
            load_match = re.search(r'load average:\s*([\d.,\s]+)', content)
            if load_match:
                summary["load_average"] = load_match.group(1).strip()
            
            cpu_match = re.search(r'%?Cpu\(s\):\s*([\d.]+)%?\s*us', content)
            if cpu_match:
                summary["cpu_user"] = float(cpu_match.group(1))
            
            mem_match = re.search(r'MiB?\s*Mem\s*:\s*([\d.]+)\s*total,\s*([\d.]+)\s*free', content)
            if mem_match:
                summary["memory_total"] = float(mem_match.group(1))
                summary["memory_free"] = float(mem_match.group(2))
        
        return summary
    
    def _parse_processes(self, screen: ParsedScreen) -> List[Dict]:
        processes = []
        
        for element in screen.elements:
            if element.element_type == ElementType.ROW:
                parts = element.content.split()
                if len(parts) >= 12:
                    try:
                        processes.append({
                            "pid": parts[0],
                            "user": parts[1],
                            "pr": parts[2],
                            "ni": parts[3],
                            "virt": parts[4],
                            "res": parts[5],
                            "shr": parts[6],
                            "s": parts[7],
                            "cpu": parts[8],
                            "mem": parts[9],
                            "time": parts[10],
                            "command": ' '.join(parts[11:])
                        })
                    except:
                        pass
        
        return processes


class VimParser(NCursesParser):
    """vim编辑器输出解析器"""
    
    def parse(self, data: str) -> ParsedScreen:
        screen = super().parse(data)
        
        screen.metadata["mode"] = self._detect_mode(screen)
        screen.metadata["filename"] = self._detect_filename(screen)
        screen.metadata["cursor"] = self._detect_cursor(screen)
        
        return screen
    
    def _detect_mode(self, screen: ParsedScreen) -> str:
        for element in screen.elements:
            if element.element_type == ElementType.STATUS:
                if '-- INSERT --' in element.content:
                    return "insert"
                elif '-- VISUAL --' in element.content:
                    return "visual"
                elif '-- REPLACE --' in element.content:
                    return "replace"
        return "normal"
    
    def _detect_filename(self, screen: ParsedScreen) -> str:
        for element in screen.elements:
            if element.element_type == ElementType.STATUS:
                match = re.search(r'"([^"]+)"', element.content)
                if match:
                    return match.group(1)
        return ""
    
    def _detect_cursor(self, screen: ParsedScreen) -> Dict:
        for element in screen.elements:
            if element.element_type == ElementType.STATUS:
                match = re.search(r'(\d+),(\d+)', element.content)
                if match:
                    return {"line": int(match.group(1)), "col": int(match.group(2))}
        return {"line": 1, "col": 1}
