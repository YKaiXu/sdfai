# Execution Result Reporting Mechanism

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

All special commands must report execution results to the source IM after execution. This is a hardcoded rule that cannot be modified by LLM.

## Hardcoded Rules

```python
HARDCODED_REPORT_RULES = {
    "REPORT_ENABLED": True,
    "REPORT_TO_SOURCE": True,
    "INCLUDE_TIMESTAMP": True,
    "INCLUDE_NCURSES_TIMESTAMP": True,
    "MODIFIABLE": False
}
```

## Report Types

| Type | Description | Content |
|------|-------------|---------|
| COM_MESSAGE_SENT | COM message sent | Delivery status + NCurses timestamp |
| SHELL_EXECUTED | Shell command executed | Execution result (success/failure) |
| ROOM_SWITCHED | Room switched | Switch result |
| PRIVATE_SENT | Private message sent | Send status |
| ERROR | Execution error | Error information |

## Report Flow

```
Command Execution → Generate Report → Message Queue → Source IM
```

## COM Message Report Example

```
✅ COM message sent
Command: com: hello
Content: hello...
Delivery time: 10:30:45
```

## Shell Command Report Example

```
✅ Shell command executed successfully
Command: ls -la
Result: total 32
drwxr-xr-x  8 user user 4096...
```

## Technical Implementation

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

## Modification Prohibited

This rule is a core system design that no module (including LLM) may modify or bypass.

---

[中文版本](execution_report.md)
