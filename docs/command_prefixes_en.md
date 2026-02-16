# Command Prefixes Specification

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

SDFAI uses hardcoded command prefixes to ensure critical operations cannot be incorrectly modified by LLM.

## Hardcoded Prefixes

```python
class CommandPrefix:
    COM_MESSAGE = "com:"        # Send COM message
    SHELL_COMMAND = "sh:"       # Execute shell command
    GO_ROOM = "g:"              # Switch room
    PRIVATE_MESSAGE = "s:"      # Private message
```

## Prefix Description

### com: - COM Message

Send message to current COM room.

```
com: Hello everyone!
com: Nice weather today
```

**Processing:**
1. Detect `com:` prefix
2. Extract message content
3. Send to current COM room

### sh: - Shell Command

Execute system shell commands.

```
sh: ls -la
sh: df -h
sh: uptime
```

**Processing:**
1. Detect `sh:` prefix
2. Extract command content
3. Execute via AsyncSSH
4. Return execution result

**Security Limits:**
- Dangerous commands require confirmation
- Timeout: 30 seconds
- Output limit: 1000 characters

### g: - Switch Room

Switch to specified COM room.

```
g: hackers
g: lounge
g: anime
```

**Processing:**
1. Detect `g:` prefix
2. Extract room name
3. Send `g <room>` to COM
4. Update current room status

### s: - Private Message

Send private message to specified user.

```
s: username This is a private message
s: friend Hello!
```

**Processing:**
1. Detect `s:` prefix
2. Parse target user and message
3. Send `s <user> <message>` to COM

## Modification Prohibited

These prefixes are hardcoded and **cannot be modified via configuration or LLM**:

```python
# This is hardcoded, cannot be modified
HARD_CODED_PREFIXES = {
    "COM_MESSAGE": "com:",
    "SHELL_COMMAND": "sh:",
    "GO_ROOM": "g:",
    "PRIVATE_MESSAGE": "s:",
}
```

## Error Handling

| Error | Handling |
|-------|----------|
| Invalid room name | Return error message |
| User not found | Return error message |
| Command timeout | Return timeout message |
| Permission denied | Return permission error |

---

[中文版本](command_prefixes.md)
