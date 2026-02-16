# Interface Specification

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Channel Interface

All communication channels must inherit from `Channel` base class:

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

## ChannelMessage Structure

```python
@dataclass
class ChannelMessage:
    channel_type: ChannelType    # Channel type
    channel_id: str              # Channel ID
    sender: str                  # Sender
    content: str                 # Message content
    timestamp: datetime          # Timestamp
    metadata: Dict[str, Any]     # Metadata
```

## File Interface

### Message File Format

Location: `data/{channel_id}/inbox/{timestamp}_{sender}.json`

```json
{
    "channel_type": "sdfcom",
    "channel_id": "main",
    "sender": "user123",
    "content": "Hello World",
    "timestamp": "2025-02-15T10:30:00"
}
```

## Skill Interface

```python
@dataclass
class SDFAISkill:
    name: str                    # Skill name
    version: str                 # Version
    description: str             # Description
    triggers: List[str]          # Trigger words
    actions: List[Dict]          # Action list
```

---

[中文版本](interface_spec.md)
