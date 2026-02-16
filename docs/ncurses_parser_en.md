# NCurses Parser

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

NCurses parser is used to parse terminal application output, such as top, htop, vim, etc. This is a core module feature that can be used for any terminal application.

## Features

- Parse ANSI escape sequences
- Extract screen elements
- Support multiple terminal applications
- Generic parsing interface

## Supported Applications

| Application | Parser | Description |
|-------------|--------|-------------|
| top | TopParser | Process monitor |
| htop | TopParser | Process monitor |
| vim | VimParser | Text editor |
| Generic | NCursesParser | Any NCurses application |

## Parsing Flow

```
Terminal Output → ANSI Strip → Screen Parse → Element Extract → Structured Data
```

## Core Classes

### NCursesParser

```python
class NCursesParser:
    def parse(self, data: str) -> ParsedScreen:
        # Parse terminal output
        pass
    
    def extract_table(self, screen: ParsedScreen) -> List[Dict]:
        # Extract table data
        pass
    
    def to_plain_text(self, screen: ParsedScreen) -> str:
        # Convert to plain text
        pass
```

### TopParser

```python
class TopParser(NCursesParser):
    def parse(self, data: str) -> ParsedScreen:
        # Parse top command output
        # Extract system summary and process list
        pass
```

### VimParser

```python
class VimParser(NCursesParser):
    def parse(self, data: str) -> ParsedScreen:
        # Parse vim editor output
        # Extract mode, filename, cursor position
        pass
```

## Data Structures

### ParsedScreen

```python
@dataclass
class ParsedScreen:
    raw_data: str              # Raw data
    elements: List[ScreenElement]  # Screen elements
    width: int = 80            # Screen width
    height: int = 24           # Screen height
    metadata: Dict[str, Any]   # Metadata
```

### ScreenElement

```python
@dataclass
class ScreenElement:
    element_type: ElementType   # Element type
    content: str               # Content
    position: Tuple[int, int]  # Position
    size: Tuple[int, int]      # Size
```

## Usage Example

```python
# Parse top command output
parser = TopParser()
screen = parser.parse(top_output)

# Get system summary
summary = screen.metadata["summary"]
print(f"CPU: {summary['cpu_user']}%")

# Get process list
processes = screen.metadata["processes"]
for proc in processes:
    print(f"{proc['pid']} {proc['command']}")
```

## Use Cases

- COM chat message parsing
- System monitoring data extraction
- Terminal application integration
- Automated operations

---

[中文版本](ncurses_parser.md)
