# Channel 通道模块

## 概述

Channel模块提供各种通讯通道的实现，包括飞书、讯飞LLM、SDF COM等。

## 通道类型

### feishu.py - 飞书通道
- **功能**: 飞书WebSocket连接
- **用途**: 接收和发送飞书消息
- **配置**: app_id, app_secret

### xunfei.py - 讯飞LLM通道
- **功能**: 讯飞星火大模型接口
- **用途**: LLM对话处理
- **配置**: app_id, api_key, api_secret

### sdfcom.py - SDF COM通道
- **功能**: SDF.org COM聊天室连接
- **用途**: COM消息收发
- **配置**: host, port, username, password

### base.py - 基础通道
- **功能**: 通道基类定义
- **类**: Channel, ChannelMessage
- **用途**: 统一通道接口

## 使用示例

```python
from channel import Channel, ChannelMessage

# 创建消息
msg = ChannelMessage(
    channel_type=ChannelType.FEISHU,
    content="Hello",
    sender="user"
)

# 发送消息
await channel.send(msg)
```
