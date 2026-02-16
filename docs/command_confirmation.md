# 命令确认机制

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

用户输入错误或模糊指令时，提示用户确认后再执行。这是硬编码规则，不可被LLM修改。

## 硬编码规则

```python
HARDCODED_CONFIRMATION_RULES = {
    "REQUIRE_CONFIRMATION": True,
    "CONFIRMATION_TIMEOUT": 60,
    "MAX_PENDING_CONFIRMATIONS": 10,
    "MODIFIABLE": False
}
```

## 触发条件

| 情况 | 说明 |
|-----|------|
| 模糊指令 | 用户输入未使用硬编码前缀，但匹配自然语言模式 |
| 危险命令 | Shell命令被标记为危险（如rm、chmod等） |
| 错误输入 | 用户输入格式不正确 |

## 确认流程

```
用户输入 → 模式匹配 → 检测模糊指令
                         ↓
                   生成建议命令
                         ↓
                   发送确认请求
                         ↓
              用户确认/取消 → 执行/终止
```

## 自然语言匹配模式

| 自然语言 | 翻译结果 |
|---------|---------|
| "切换到xxx聊天室" | `g: xxx` |
| "去xxx房间" | `g: xxx` |
| "进入xxx频道" | `g: xxx` |
| "私聊xxx说yyy" | `s: xxx yyy` |
| "给xxx发yyy" | `s: xxx yyy` |
| "发送xxx到com" | `com: xxx` |
| "在com说xxx" | `com: xxx` |
| "执行xxx命令" | `sh: xxx` |

## 确认请求示例

```
⚠️ 指令确认请求

您的输入: "切换到anonradio聊天室"
识别为: 房间切换
建议指令: `g: anonradio`

━━━━━━━━━━━━━━━━━━━━━━
回复 "confirm conf_abc123" 确认执行
回复 "reject conf_abc123" 取消
回复 "cancel" 取消所有待确认
━━━━━━━━━━━━━━━━━━━━━━
```

## 危险命令列表

| 命令 | 风险级别 |
|-----|---------|
| rm | 高 |
| chmod | 高 |
| chown | 高 |
| kill | 高 |
| dd | 高 |
| mkfs | 高 |

## 技术实现

```python
class CommandConfirmation:
    def analyze_input(self, user_input: str) -> Optional[PendingConfirmation]:
        if self._has_explicit_prefix(user_input):
            return None
        
        for cmd_type, config in self.FUZZY_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, user_input):
                    return self._create_confirmation(...)
        
        return None
```

## 禁止修改

此规则为系统核心设计，任何模块（包括LLM）不得修改或绕过。

---

[English Version](command_confirmation_en.md)
