# 命令前缀规范

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

SDFAI使用硬编码的命令前缀，确保关键操作不会被LLM错误修改。

## 硬编码前缀

```python
class CommandPrefix:
    COM_MESSAGE = "com:"        # 发送COM消息
    SHELL_COMMAND = "sh:"       # 执行Shell命令
    GO_ROOM = "g:"              # 切换房间
    PRIVATE_MESSAGE = "s:"      # 私聊
```

## 前缀说明

### com: - COM消息

发送消息到当前COM房间。

```
com: 大家好！
com: 今天天气不错
```

**处理流程:**
1. 检测 `com:` 前缀
2. 提取消息内容
3. 发送到当前COM房间

### sh: - Shell命令

执行系统Shell命令。

```
sh: ls -la
sh: df -h
sh: uptime
```

**处理流程:**
1. 检测 `sh:` 前缀
2. 提取命令内容
3. 通过AsyncSSH执行
4. 返回执行结果

**安全限制:**
- 危险命令需要确认
- 超时限制: 30秒
- 输出限制: 1000字符

### g: - 切换房间

切换到指定的COM房间。

```
g: hackers
g: lounge
g: anime
```

**处理流程:**
1. 检测 `g:` 前缀
2. 提取房间名
3. 发送 `g <room>` 到COM
4. 更新当前房间状态

### s: - 私聊

发送私聊消息给指定用户。

```
s: username 这是私聊消息
s: friend 你好！
```

**处理流程:**
1. 检测 `s:` 前缀
2. 解析目标用户和消息
3. 发送 `s <user> <message>` 到COM

## 禁止修改

这些前缀在代码中硬编码，**不可通过配置或LLM修改**：

```python
# 这是硬编码，不可修改
HARD_CODED_PREFIXES = {
    "COM_MESSAGE": "com:",
    "SHELL_COMMAND": "sh:",
    "GO_ROOM": "g:",
    "PRIVATE_MESSAGE": "s:",
}
```

## 错误处理

| 错误 | 处理方式 |
|-----|---------|
| 无效房间名 | 返回错误提示 |
| 用户不存在 | 返回错误提示 |
| 命令超时 | 返回超时提示 |
| 权限不足 | 返回权限错误 |

---

[English Version](command_prefixes_en.md)
