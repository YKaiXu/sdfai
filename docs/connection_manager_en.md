# Connection Manager

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

Connection Manager is a core module feature that manages all types of connections (SSH, WebSocket, HTTP, etc.).

## Supported Connection Types

| Type | Description |
|------|-------------|
| SSH | SSH connection (using asyncssh) |
| WebSocket | WebSocket connection |
| HTTP | HTTP connection |
| Serial | Serial port connection |
| Telnet | Telnet connection |

## Core Classes

### ConnectionManager

```python
class ConnectionManager:
    def register(self, connection: Connection) -> str:
        # Register connection
        pass
    
    def get(self, connection_id: str) -> Connection:
        # Get connection
        pass
    
    async def connect_all(self) -> Dict[str, bool]:
        # Connect all
        pass
    
    async def disconnect_all(self) -> Dict[str, bool]:
        # Disconnect all
        pass
```

### Connection

```python
class Connection(Generic[T]):
    async def connect(self) -> bool:
        # Establish connection
        pass
    
    async def disconnect(self) -> bool:
        # Disconnect
        pass
    
    async def send(self, data: Any) -> bool:
        # Send data
        pass
    
    async def receive(self) -> Any:
        # Receive data
        pass
```

### SSHConnection

```python
class SSHConnection(Connection):
    async def execute(self, command: str, timeout: int = 30) -> str:
        # Execute SSH command
        pass
    
    async def open_session(self) -> tuple:
        # Open session
        pass
```

## Usage Example

```python
# Create connection manager
manager = ConnectionManager(data_dir)

# Create SSH connection
ssh_info = SSHConnectionInfo(
    connection_id="sdf_org",
    host="sdf.org",
    port=22,
    username="user",
    password="pass"
)
ssh_conn = SSHConnection(ssh_info)

# Register and connect
manager.register(ssh_conn)
await ssh_conn.connect()

# Execute command
result = await ssh_conn.execute("ls -la")
```

## Connection States

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
```

## Callback Mechanism

```python
# Connection callbacks
connection.on_connect(callback)
connection.on_disconnect(callback)
connection.on_error(callback)
```

## Design Principles

1. **Generality**: Support multiple connection types
2. **Extensibility**: Easy to add new connection types
3. **Async**: Fully asynchronous design
4. **State Management**: Automatic connection state management

---

[中文版本](connection_manager.md)
