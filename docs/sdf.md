# SDF 连接模块

## 概述

SDF模块提供与SDF.org系统的连接和交互功能。

## 组件

### client.py - SDF客户端
- **功能**: SDF系统客户端
- **类**: SDFClient, SDFConfig
- **用途**: 连接SDF.org系统

### com.py - COM聊天
- **功能**: COM聊天室交互
- **类**: COMConnection
- **用途**: 发送/接收COM消息

### connection.py - 连接管理
- **功能**: SSH连接管理
- **类**: SSHConnection
- **用途**: 管理SSH连接

### commands.py - 命令处理
- **功能**: SDF命令处理
- **类**: SDFCommands
- **用途**: 执行SDF系统命令

## 使用示例

```python
from sdf import SDFClient, SDFConfig

# 创建客户端
config = SDFConfig(
    host="sdf.org",
    port=22,
    username="user",
    password="pass"
)
client = SDFClient(config)

# 连接
await client.connect()

# 进入COM聊天室
await client.enter_com("lobby")

# 发送消息
await client.send_com_message("Hello!")

# 切换房间
await client.switch_room("hackers")

# 断开连接
await client.disconnect()
```

## COM聊天室

SDF.org的COM系统是一个多房间聊天系统：

- lobby: 大厅
- hackers: 黑客讨论
- arcade: 游戏讨论
- bboard: 公告板
- misc: 杂项讨论
