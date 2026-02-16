# 执行结果报告机制

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

所有特殊指令执行后，必须向指令发出的IM报告执行结果。这是硬编码规则，不可被LLM修改。

## 硬编码规则

```python
HARDCODED_REPORT_RULES = {
    "REPORT_ENABLED": True,
    "REPORT_TO_SOURCE": True,
    "INCLUDE_TIMESTAMP": True,
    "INCLUDE_NCURSES_TIMESTAMP": True,
    "MODIFIABLE": False
}
```

## 报告类型

| 类型 | 说明 | 内容 |
|-----|------|------|
| COM_MESSAGE_SENT | COM消息发送 | 送达状态 + NCurses时间戳 |
| SHELL_EXECUTED | Shell命令执行 | 执行结果（成功/失败） |
| ROOM_SWITCHED | 房间切换 | 切换结果 |
| PRIVATE_SENT | 私聊发送 | 发送状态 |
| ERROR | 执行错误 | 错误信息 |

## 报告流程

```
指令执行 → 生成报告 → 消息队列 → 源IM
```

## COM消息报告示例

```
✅ COM消息已发送
命令: com: hello
内容: hello...
送达时间: 10:30:45
```

## Shell命令报告示例

```
✅ Shell命令执行成功
命令: ls -la
结果: total 32
drwxr-xr-x  8 user user 4096...
```

## 技术实现

```python
class ExecutionReporter:
    def report_com_sent(self, source_im, source_user, command, content, ncurses_timestamp):
        return self.create_report(
            report_type=ReportType.COM_MESSAGE_SENT,
            source_im=source_im,
            source_user=source_user,
            command=command,
            success=True,
            message=content,
            ncurses_timestamp=ncurses_timestamp
        )
```

## 禁止修改

此规则为系统核心设计，任何模块（包括LLM）不得修改或绕过。

---

[English Version](execution_report_en.md)
