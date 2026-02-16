# 连接管理器

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

连接管理器是core模块的通用功能，管理所有类型的连接（SSH、WebSocket、HTTP等）。

## 支持的连接类型

| 类型 | 说明 |
|-----|------|
| SSH | SSH连接（使用asyncssh） |
| WebSocket | WebSocket连接 |
| HTTP | HTTP连接 |
| Serial | 串口连接 |
| Telnet | Telnet连接 |

## 核心类

### ConnectionManager

```python
class ConnectionManager:
    def register(self, connection: Connection) -> str:
        # 注册连接
        pass
    
    def get(self, connection_id: str) -> Connection:
        # 获取连接
        pass
    
    async def connect_all(self) -> Dict[str, bool]:
        # 连接所有
        pass
    
    async def disconnect_all(self) -> Dict[str, bool]:
        # 断开所有
        pass
```

### Connection

```python
class Connection(Generic[T]):
    async def connect(self) -> bool:
        # 建立连接
        pass
    
    async def disconnect(self) -> bool:
        # 断开连接
        pass
    
    async def send(self, data: Any) -> bool:
        # 发送数据
        pass
    
    async def receive(self) -> Any:
        # 接收数据
        pass
```

### SSHConnection

```python
class SSHConnection(Connection):
    async def execute(self, command: str, timeout: int = 30) -> str:
        # 执行SSH命令
        pass
    
    async def open_session(self) -> tuple:
        # 打开会话
        pass
```

## 使用示例

```python
# 创建连接管理器
manager = ConnectionManager(data_dir)

# 创建SSH连接
ssh_info = SSHConnectionInfo(
    connection_id="sdf_org",
    host="sdf.org",
    port=22,
    username="user",
    password="pass"
)
ssh_conn = SSHConnection(ssh_info)

# 注册并连接
manager.register(ssh_conn)
await ssh_conn.connect()

# 执行命令
result = await ssh_conn.execute("ls -la")
```

## 连接状态

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
```

## 回调机制

```python
# 连接回调
connection.on_connect(callback)
connection.on_disconnect(callback)
connection.on_error(callback)
```

## 设计原则

1. **通用性**: 支持多种连接类型
2. **可扩展**: 易于添加新连接类型
3. **异步**: 完全异步设计
4. **状态管理**: 自动管理连接状态

---

[English Version](connection_manager_en.md)
