# 接口规范

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## Channel 接口

所有通讯通道必须继承 `Channel` 基类：

```python
from channel.base import Channel, ChannelMessage, ChannelType

class MyChannel(Channel):
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.CUSTOM
    
    async def connect(self) -> bool:
        pass
    
    async def disconnect(self) -> bool:
        pass
    
    async def send(self, message: ChannelMessage) -> bool:
        pass
    
    async def receive(self) -> AsyncIterator[ChannelMessage]:
        pass
```

## ChannelMessage 结构

```python
@dataclass
class ChannelMessage:
    channel_type: ChannelType    # 通道类型
    channel_id: str              # 通道ID
    sender: str                  # 发送者
    content: str                 # 消息内容
    timestamp: datetime          # 时间戳
    metadata: Dict[str, Any]     # 元数据
```

## 文件接口

### 消息文件格式

位置: `data/{channel_id}/inbox/{timestamp}_{sender}.json`

```json
{
    "channel_type": "sdfcom",
    "channel_id": "main",
    "sender": "user123",
    "content": "Hello World",
    "timestamp": "2025-02-15T10:30:00"
}
```

## Skill 接口

```python
@dataclass
class SDFAISkill:
    name: str                    # 技能名称
    version: str                 # 版本
    description: str             # 描述
    triggers: List[str]          # 触发词
    actions: List[Dict]          # 动作列表
```

---

[English Version](interface_spec_en.md)
