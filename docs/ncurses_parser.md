# NCurses解析器

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

NCurses解析器用于解析终端应用的输出，如top、htop、vim等。这是core模块的通用功能，可用于任何终端应用。

## 功能特点

- 解析ANSI转义序列
- 提取屏幕元素
- 支持多种终端应用
- 通用解析接口

## 支持的应用

| 应用 | 解析器 | 说明 |
|-----|-------|------|
| top | TopParser | 进程监控 |
| htop | TopParser | 进程监控 |
| vim | VimParser | 文本编辑器 |
| 通用 | NCursesParser | 任何NCurses应用 |

## 解析流程

```
终端输出 → ANSI剥离 → 屏幕解析 → 元素提取 → 结构化数据
```

## 核心类

### NCursesParser

```python
class NCursesParser:
    def parse(self, data: str) -> ParsedScreen:
        # 解析终端输出
        pass
    
    def extract_table(self, screen: ParsedScreen) -> List[Dict]:
        # 提取表格数据
        pass
    
    def to_plain_text(self, screen: ParsedScreen) -> str:
        # 转换为纯文本
        pass
```

### TopParser

```python
class TopParser(NCursesParser):
    def parse(self, data: str) -> ParsedScreen:
        # 解析top命令输出
        # 提取系统摘要和进程列表
        pass
```

### VimParser

```python
class VimParser(NCursesParser):
    def parse(self, data: str) -> ParsedScreen:
        # 解析vim编辑器输出
        # 提取模式、文件名、光标位置
        pass
```

## 数据结构

### ParsedScreen

```python
@dataclass
class ParsedScreen:
    raw_data: str              # 原始数据
    elements: List[ScreenElement]  # 屏幕元素
    width: int = 80            # 屏幕宽度
    height: int = 24           # 屏幕高度
    metadata: Dict[str, Any]   # 元数据
```

### ScreenElement

```python
@dataclass
class ScreenElement:
    element_type: ElementType   # 元素类型
    content: str               # 内容
    position: Tuple[int, int]  # 位置
    size: Tuple[int, int]      # 尺寸
```

## 使用示例

```python
# 解析top命令输出
parser = TopParser()
screen = parser.parse(top_output)

# 获取系统摘要
summary = screen.metadata["summary"]
print(f"CPU: {summary['cpu_user']}%")

# 获取进程列表
processes = screen.metadata["processes"]
for proc in processes:
    print(f"{proc['pid']} {proc['command']}")
```

## 应用场景

- COM聊天消息解析
- 系统监控数据提取
- 终端应用集成
- 自动化运维

---

[English Version](ncurses_parser_en.md)
