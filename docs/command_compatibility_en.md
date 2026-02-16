# Command Compatibility Guide

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

SDFAI supports multiple command systems:
- **SDF.org Specific Commands**: COM chat system commands
- **Linux General Commands**: Standard Linux system commands
- **Natural Language Commands**: Translated to system commands via LLM

## SDF.org COM Commands

### Chat Commands

| Command | Description | Example |
|---------|-------------|---------|
| `g <room>` | Switch room | `g hackers` |
| `s <user> <msg>` | Private message | `s tom Hello` |
| `w` | Who is online | `w` |
| `l` | List rooms | `l` |
| `i` | Room info | `i` |
| `q` | Quit COM | `q` |
| `h` | Help | `h` |

### Usage

Execute via hardcoded prefixes:

```
g: hackers        # Switch to hackers room
s: tom Hello!     # Send private message to tom
com: Hello all!   # Send message to current room
```

## Linux General Commands

### File Operations

| Command | Description | Example |
|---------|-------------|---------|
| `ls` | List files | `sh: ls -la` |
| `cd` | Change directory | `sh: cd /home` |
| `cat` | View file | `sh: cat /etc/hosts` |
| `grep` | Search text | `sh: grep error /var/log/syslog` |
| `find` | Find files | `sh: find / -name "*.py"` |

### System Information

| Command | Description | Example |
|---------|-------------|---------|
| `uptime` | Uptime | `sh: uptime` |
| `df` | Disk space | `sh: df -h` |
| `free` | Memory usage | `sh: free -m` |
| `top` | Process monitor | `sh: top -n 1` |
| `ps` | Process list | `sh: ps aux` |

### User Management

| Command | Description | Example |
|---------|-------------|---------|
| `whoami` | Current user | `sh: whoami` |
| `id` | User info | `sh: id` |
| `who` | Logged in users | `sh: who` |

## Natural Language Commands

SDFAI translates natural language to system commands via LLM:

### Examples

| Natural Language | Translation |
|-----------------|-------------|
| "switch to hackers room" | `g hackers` |
| "show disk space" | `df -h` |
| "show current directory" | `pwd` |
| "show system load" | `uptime` |

### Translation Flow

```
User Input → LLM Translation → Security Evaluation → User Confirmation → Execute
```

## Security Restrictions

### Dangerous Commands (Require Confirmation)

- `rm -rf`
- `dd if=`
- `mkfs`
- `chmod 777`
- `chown`

### Prohibited Commands

- `rm -rf /`
- `:(){ :|:& };:` (fork bomb)
- Commands exposing passwords

## Extended Commands

Custom commands can be added via skill system:

```python
# skills/installed/my_commands/handler.py
async def handle(text, trigger, skill, context):
    if "backup" in text:
        return "sh: tar -czf backup.tar.gz /home"
    return None
```

---

[中文版本](command_compatibility.md)
