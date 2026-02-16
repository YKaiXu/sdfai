"""
Thread Manager - 线程管理器
管理异步任务和线程池
"""
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json


@dataclass
class TaskInfo:
    task_id: str
    name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Any = None
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class ThreadManager:
    def __init__(self, data_dir: Path, max_workers: int = 10):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._task_info: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._task_counter = 0
    
    def generate_task_id(self) -> str:
        with self._lock:
            self._task_counter += 1
            return f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._task_counter}"
    
    async def submit_async(
        self, 
        coro: Coroutine, 
        name: str = "",
        callback: Callable = None
    ) -> str:
        task_id = self.generate_task_id()
        
        info = TaskInfo(
            task_id=task_id,
            name=name or coro.__name__ if hasattr(coro, '__name__') else "unknown",
            status="pending",
            created_at=datetime.now()
        )
        self._task_info[task_id] = info
        
        async def wrapped_task():
            info.status = "running"
            info.started_at = datetime.now()
            
            try:
                result = await coro
                info.status = "completed"
                info.result = result
                info.completed_at = datetime.now()
                
                if callback:
                    await self._run_callback(callback, result, None)
                
                return result
            except Exception as e:
                info.status = "failed"
                info.error = str(e)
                info.completed_at = datetime.now()
                
                if callback:
                    await self._run_callback(callback, None, e)
                
                raise
        
        task = asyncio.create_task(wrapped_task())
        self._tasks[task_id] = task
        
        return task_id
    
    def submit_sync(self, func: Callable, *args, name: str = "", callback: Callable = None, **kwargs) -> str:
        task_id = self.generate_task_id()
        
        info = TaskInfo(
            task_id=task_id,
            name=name or func.__name__,
            status="pending",
            created_at=datetime.now()
        )
        self._task_info[task_id] = info
        
        def wrapped_func():
            info.status = "running"
            info.started_at = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                info.status = "completed"
                info.result = result
                info.completed_at = datetime.now()
                return result
            except Exception as e:
                info.status = "failed"
                info.error = str(e)
                info.completed_at = datetime.now()
                raise
        
        future = self._executor.submit(wrapped_func)
        
        if callback:
            future.add_done_callback(
                lambda f: self._sync_callback_wrapper(f, callback)
            )
        
        return task_id
    
    async def _run_callback(self, callback: Callable, result: Any, error: Exception):
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(result, error)
            else:
                callback(result, error)
        except Exception as e:
            pass
    
    def _sync_callback_wrapper(self, future, callback):
        try:
            result = future.result()
            callback(result, None)
        except Exception as e:
            callback(None, e)
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        return self._task_info.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if not task.done():
                task.cancel()
                if task_id in self._task_info:
                    self._task_info[task_id].status = "cancelled"
                return True
        return False
    
    def get_all_tasks(self) -> List[TaskInfo]:
        return list(self._task_info.values())
    
    def get_active_tasks(self) -> List[TaskInfo]:
        return [
            info for info in self._task_info.values()
            if info.status in ["pending", "running"]
        ]
    
    def cleanup_completed(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now()
        to_remove = []
        
        for task_id, info in self._task_info.items():
            if info.status in ["completed", "failed", "cancelled"]:
                if info.completed_at:
                    age_hours = (cutoff - info.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._task_info[task_id]
            if task_id in self._tasks:
                del self._tasks[task_id]
        
        return len(to_remove)
    
    async def wait_for_task(self, task_id: str, timeout: float = None) -> Any:
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        
        if timeout:
            return await asyncio.wait_for(task, timeout=timeout)
        else:
            return await task
    
    async def shutdown(self, wait: bool = True):
        for task_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
        
        if wait:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        
        self._executor.shutdown(wait=wait)
    
    def save_state(self):
        state_file = self.data_dir / "thread_state.json"
        state = {
            "updated_at": datetime.now().isoformat(),
            "tasks": [info.to_dict() for info in self._task_info.values()]
        }
        state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def load_state(self):
        state_file = self.data_dir / "thread_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding='utf-8'))
                for task_data in state.get("tasks", []):
                    info = TaskInfo(
                        task_id=task_data["task_id"],
                        name=task_data["name"],
                        status=task_data["status"],
                        created_at=datetime.fromisoformat(task_data["created_at"]) if task_data.get("created_at") else None,
                        started_at=datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None,
                        completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None,
                        error=task_data.get("error")
                    )
                    self._task_info[info.task_id] = info
            except:
                pass
