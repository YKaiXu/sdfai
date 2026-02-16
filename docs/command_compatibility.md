# 命令兼容指南

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

SDFAI支持多种命令系统，包括：
- **SDF.org专用命令**: COM聊天系统命令
- **Linux通用命令**: 标准Linux系统命令
- **自然语言命令**: 通过LLM翻译为系统命令

## SDF.org COM命令

### 聊天命令

| 命令 | 说明 | 示例 |
|-----|------|------|
| `g <room>` | 切换房间 | `g hackers` |
| `s <user> <msg>` | 私聊 | `s tom 你好` |
| `w` | 查看在线用户 | `w` |
| `l` | 列出房间 | `l` |
| `i` | 房间信息 | `i` |
| `q` | 退出COM | `q` |
| `h` | 帮助 | `h` |

### 使用方式

通过硬编码前缀执行：

```
g: hackers        # 切换到hackers房间
s: tom 你好！     # 给tom发私聊
com: 大家好！     # 发送消息到当前房间
```

## Linux通用命令

### 文件操作

| 命令 | 说明 | 示例 |
|-----|------|------|
| `ls` | 列出文件 | `sh: ls -la` |
| `cd` | 切换目录 | `sh: cd /home` |
| `cat` | 查看文件 | `sh: cat /etc/hosts` |
| `grep` | 搜索文本 | `sh: grep error /var/log/syslog` |
| `find` | 查找文件 | `sh: find / -name "*.py"` |

### 系统信息

| 命令 | 说明 | 示例 |
|-----|------|------|
| `uptime` | 运行时间 | `sh: uptime` |
| `df` | 磁盘空间 | `sh: df -h` |
| `free` | 内存使用 | `sh: free -m` |
| `top` | 进程监控 | `sh: top -n 1` |
| `ps` | 进程列表 | `sh: ps aux` |

### 用户管理

| 命令 | 说明 | 示例 |
|-----|------|------|
| `whoami` | 当前用户 | `sh: whoami` |
| `id` | 用户信息 | `sh: id` |
| `who` | 登录用户 | `sh: who` |

## 自然语言命令

SDFAI通过LLM将自然语言翻译为系统命令：

### 示例

| 自然语言 | 翻译结果 |
|---------|---------|
| "切换到hackers房间" | `g hackers` |
| "查看磁盘空间" | `df -h` |
| "显示当前目录" | `pwd` |
| "查看系统负载" | `uptime` |

### 翻译流程

```
用户输入 → LLM翻译 → 安全评估 → 用户确认 → 执行
```

## 安全限制

### 危险命令（需要确认）

- `rm -rf`
- `dd if=`
- `mkfs`
- `chmod 777`
- `chown`

### 禁止命令

- `rm -rf /`
- `:(){ :|:& };:` (fork bomb)
- 直接暴露密码的命令

## 扩展命令

可通过技能系统扩展自定义命令：

```python
# skills/installed/my_commands/handler.py
async def handle(text, trigger, skill, context):
    if "备份" in text:
        return "sh: tar -czf backup.tar.gz /home"
    return None
```

---

[English Version](command_compatibility_en.md)
