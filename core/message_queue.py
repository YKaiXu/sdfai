"""
Message Queue - 消息队列管理
支持优先级队列和持久化
"""
import asyncio
import json
import heapq
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass(order=True)
class QueueMessage:
    priority: int
    message_id: str = field(compare=False)
    content: Any = field(compare=False)
    source: str = field(compare=False, default="")
    target: str = field(compare=False, default="")
    created_at: datetime = field(compare=False, default_factory=datetime.now)
    status: MessageStatus = field(compare=False, default=MessageStatus.PENDING)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    metadata: Dict = field(compare=False, default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "priority": self.priority,
            "content": self.content,
            "source": self.source,
            "target": self.target,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QueueMessage':
        return cls(
            priority=data["priority"],
            message_id=data["message_id"],
            content=data["content"],
            source=data.get("source", ""),
            target=data.get("target", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=MessageStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            metadata=data.get("metadata", {})
        )


class MessageQueue:
    def __init__(self, data_dir: Path, queue_name: str = "default"):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue_name = queue_name
        
        self._queue: List[QueueMessage] = []
        self._processing: Dict[str, QueueMessage] = {}
        self._handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
    
    def generate_message_id(self) -> str:
        return f"msg_{uuid.uuid4().hex[:12]}"
    
    async def put(
        self,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        source: str = "",
        target: str = "",
        metadata: Dict = None
    ) -> str:
        message = QueueMessage(
            priority=priority.value,
            message_id=self.generate_message_id(),
            content=content,
            source=source,
            target=target,
            metadata=metadata or {}
        )
        
        async with self._lock:
            heapq.heappush(self._queue, message)
            self._not_empty.set()
        
        await self._persist_message(message)
        
        return message.message_id
    
    async def get(self, timeout: float = None) -> Optional[QueueMessage]:
        async with self._lock:
            if not self._queue:
                self._not_empty.clear()
        
        if timeout:
            try:
                await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
        
        async with self._lock:
            if not self._queue:
                return None
            
            message = heapq.heappop(self._queue)
            message.status = MessageStatus.PROCESSING
            self._processing[message.message_id] = message
            
            if not self._queue:
                self._not_empty.clear()
        
        await self._update_message_status(message)
        
        return message
    
    async def ack(self, message_id: str, success: bool = True, error: str = None):
        async with self._lock:
            if message_id not in self._processing:
                return
            
            message = self._processing[message_id]
            
            if success:
                message.status = MessageStatus.COMPLETED
                del self._processing[message_id]
            else:
                if message.retry_count < message.max_retries:
                    message.status = MessageStatus.RETRY
                    message.retry_count += 1
                    heapq.heappush(self._queue, message)
                    del self._processing[message_id]
                else:
                    message.status = MessageStatus.FAILED
                    message.metadata["error"] = error
                    del self._processing[message_id]
        
        await self._update_message_status(message)
    
    def register_handler(self, message_type: str, handler: Callable):
        self._handlers[message_type] = handler
    
    async def start_processing(self):
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_loop())
    
    async def stop_processing(self):
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
    
    async def _process_loop(self):
        while self._running:
            message = await self.get(timeout=1.0)
            
            if message is None:
                continue
            
            try:
                handler = self._handlers.get(message.target)
                
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(message)
                    else:
                        result = handler(message)
                    
                    await self.ack(message.message_id, success=True)
                else:
                    await self.ack(message.message_id, success=True)
                    
            except Exception as e:
                await self.ack(message.message_id, success=False, error=str(e))
    
    async def _persist_message(self, message: QueueMessage):
        queue_file = self.data_dir / f"queue_{self.queue_name}.json"
        
        messages = []
        if queue_file.exists():
            try:
                messages = json.loads(queue_file.read_text(encoding='utf-8'))
            except:
                pass
        
        messages.append(message.to_dict())
        
        queue_file.write_text(
            json.dumps(messages, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    async def _update_message_status(self, message: QueueMessage):
        queue_file = self.data_dir / f"queue_{self.queue_name}.json"
        
        if not queue_file.exists():
            return
        
        try:
            messages = json.loads(queue_file.read_text(encoding='utf-8'))
            
            for i, msg_data in enumerate(messages):
                if msg_data["message_id"] == message.message_id:
                    messages[i] = message.to_dict()
                    break
            
            queue_file.write_text(
                json.dumps(messages, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except:
            pass
    
    def get_queue_size(self) -> int:
        return len(self._queue)
    
    def get_processing_count(self) -> int:
        return len(self._processing)
    
    def get_stats(self) -> Dict:
        return {
            "queue_name": self.queue_name,
            "queue_size": len(self._queue),
            "processing": len(self._processing),
            "running": self._running,
            "handlers": list(self._handlers.keys())
        }
    
    async def load_persisted(self):
        queue_file = self.data_dir / f"queue_{self.queue_name}.json"
        
        if not queue_file.exists():
            return
        
        try:
            messages = json.loads(queue_file.read_text(encoding='utf-8'))
            
            for msg_data in messages:
                if msg_data["status"] in ["pending", "retry"]:
                    message = QueueMessage.from_dict(msg_data)
                    heapq.heappush(self._queue, message)
            
            if self._queue:
                self._not_empty.set()
                
        except:
            pass
    
    async def clear_completed(self):
        queue_file = self.data_dir / f"queue_{self.queue_name}.json"
        
        if not queue_file.exists():
            return
        
        try:
            messages = json.loads(queue_file.read_text(encoding='utf-8'))
            
            messages = [
                m for m in messages
                if m["status"] not in ["completed", "failed"]
            ]
            
            queue_file.write_text(
                json.dumps(messages, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except:
            pass


class QueueManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._queues: Dict[str, MessageQueue] = {}
    
    def get_queue(self, name: str) -> MessageQueue:
        if name not in self._queues:
            self._queues[name] = MessageQueue(self.data_dir, name)
        return self._queues[name]
    
    async def broadcast(self, content: Any, priority: MessagePriority = MessagePriority.NORMAL):
        for queue in self._queues.values():
            await queue.put(content, priority)
    
    def get_all_stats(self) -> Dict:
        return {
            name: queue.get_stats()
            for name, queue in self._queues.items()
        }
    
    async def start_all(self):
        for queue in self._queues.values():
            await queue.start_processing()
    
    async def stop_all(self):
        for queue in self._queues.values():
            await queue.stop_processing()
