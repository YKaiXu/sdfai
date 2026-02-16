"""
SDFAI Core Daemon - 核心守护进程
管理SDFAI核心服务，模块升级通知
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DaemonStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModuleInfo:
    name: str
    version: str
    installed_at: datetime
    source: str
    file_path: str
    latest_version: Optional[str] = None
    upgrade_available: bool = False


@dataclass
class UpgradeRequest:
    module_name: str
    current_version: str
    new_version: str
    requested_at: datetime
    confirmed: bool = False
    confirmed_by: Optional[str] = None


class CoreDaemon:
    CORE_VERSION = "1.0.0"
    CORE_MODULES = [
        "channel",
        "core",
        "sdf",
        "storage",
        "skills"
    ]
    
    def __init__(self, data_dir: Path, im_notifier: Callable = None):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.im_notifier = im_notifier
        
        self.status = DaemonStatus.STOPPED
        self.modules: Dict[str, ModuleInfo] = {}
        self.pending_upgrades: Dict[str, UpgradeRequest] = {}
        
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._upgrade_check_task: Optional[asyncio.Task] = None
    
    async def start(self):
        if self._running:
            return
        
        self.status = DaemonStatus.STARTING
        self._running = True
        
        await self._load_modules()
        
        self._main_task = asyncio.create_task(self._main_loop())
        self._upgrade_check_task = asyncio.create_task(self._upgrade_check_loop())
        
        self.status = DaemonStatus.RUNNING
        await self._save_daemon_state()
    
    async def stop(self):
        if not self._running:
            return
        
        self.status = DaemonStatus.STOPPING
        self._running = False
        
        if self._main_task:
            self._main_task.cancel()
        if self._upgrade_check_task:
            self._upgrade_check_task.cancel()
        
        await self._save_daemon_state()
        self.status = DaemonStatus.STOPPED
    
    async def _main_loop(self):
        while self._running:
            try:
                await self._health_check()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.status = DaemonStatus.ERROR
                await self._save_daemon_state()
    
    async def _upgrade_check_loop(self):
        while self._running:
            try:
                await self._check_module_upgrades()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass
    
    async def _load_modules(self):
        modules_file = self.data_dir / "modules.json"
        
        if modules_file.exists():
            try:
                data = json.loads(modules_file.read_text(encoding='utf-8'))
                for name, info in data.get("modules", {}).items():
                    self.modules[name] = ModuleInfo(
                        name=name,
                        version=info["version"],
                        installed_at=datetime.fromisoformat(info["installed_at"]),
                        source=info["source"],
                        file_path=info["file_path"]
                    )
            except:
                pass
        
        await self._scan_local_modules()
    
    async def _scan_local_modules(self):
        for module_name in self.CORE_MODULES:
            module_dir = self.data_dir.parent / module_name
            if module_dir.exists():
                version = await self._get_module_version(module_dir)
                
                if module_name not in self.modules:
                    self.modules[module_name] = ModuleInfo(
                        name=module_name,
                        version=version,
                        installed_at=datetime.now(),
                        source="local",
                        file_path=str(module_dir)
                    )
                else:
                    self.modules[module_name].version = version
    
    async def _get_module_version(self, module_dir: Path) -> str:
        version_file = module_dir / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        
        init_file = module_dir / "__init__.py"
        if init_file.exists():
            content = init_file.read_text(encoding='utf-8')
            import re
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        
        return "0.0.0"
    
    async def _check_module_upgrades(self):
        for name, module in self.modules.items():
            if module.source == "pip":
                latest = await self._get_pip_latest_version(name)
                if latest and latest != module.version:
                    module.latest_version = latest
                    module.upgrade_available = True
                    
                    await self._notify_upgrade_available(module)
            
            elif module.source == "git":
                latest = await self._get_git_latest_version(module.file_path)
                if latest and latest != module.version:
                    module.latest_version = latest
                    module.upgrade_available = True
                    
                    await self._notify_upgrade_available(module)
    
    async def _get_pip_latest_version(self, package: str) -> Optional[str]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "index", "versions", package],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            import re
            match = re.search(r'Available versions:\s*([\d.,\s]+)', result.stdout)
            if match:
                versions = match.group(1).split(',')
                return versions[0].strip()
        except:
            pass
        
        return None
    
    async def _get_git_latest_version(self, repo_path: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "fetch", "--dry-run"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                return "update_available"
        except:
            pass
        
        return None
    
    async def _notify_upgrade_available(self, module: ModuleInfo):
        if not self.im_notifier:
            return
        
        upgrade_id = f"{module.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self.pending_upgrades[upgrade_id] = UpgradeRequest(
            module_name=module.name,
            current_version=module.version,
            new_version=module.latest_version,
            requested_at=datetime.now()
        )
        
        message = f"""
🔄 模块升级可用

模块: {module.name}
当前版本: {module.version}
新版本: {module.latest_version}

回复 "upgrade {upgrade_id}" 确认升级
回复 "skip {upgrade_id}" 跳过此次升级
"""
        
        await self.im_notifier(message, {
            "type": "upgrade_available",
            "upgrade_id": upgrade_id,
            "module": module.name
        })
    
    async def confirm_upgrade(self, upgrade_id: str, confirmed_by: str = "user") -> bool:
        if upgrade_id not in self.pending_upgrades:
            return False
        
        request = self.pending_upgrades[upgrade_id]
        request.confirmed = True
        request.confirmed_by = confirmed_by
        
        module = self.modules.get(request.module_name)
        if not module:
            return False
        
        success = await self._execute_upgrade(module)
        
        if success:
            module.version = request.new_version
            module.upgrade_available = False
            del self.pending_upgrades[upgrade_id]
            
            if self.im_notifier:
                await self.im_notifier(
                    f"✅ 模块 {module.name} 已成功升级到 {request.new_version}",
                    {"type": "upgrade_completed", "module": module.name}
                )
        
        await self._save_daemon_state()
        return success
    
    async def _execute_upgrade(self, module: ModuleInfo) -> bool:
        try:
            if module.source == "pip":
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", module.name],
                    capture_output=True,
                    timeout=300
                )
                return result.returncode == 0
            
            elif module.source == "git":
                result = subprocess.run(
                    ["git", "pull"],
                    cwd=module.file_path,
                    capture_output=True,
                    timeout=60
                )
                return result.returncode == 0
            
            return False
        except:
            return False
    
    async def _health_check(self):
        for name, module in self.modules.items():
            module_path = Path(module.file_path)
            if not module_path.exists():
                if self.im_notifier:
                    await self.im_notifier(
                        f"⚠️ 模块 {name} 路径不存在: {module.file_path}",
                        {"type": "module_error", "module": name}
                    )
    
    async def _save_daemon_state(self):
        state_file = self.data_dir / "daemon_state.json"
        
        state = {
            "status": self.status.value,
            "core_version": self.CORE_VERSION,
            "updated_at": datetime.now().isoformat(),
            "modules": {
                name: {
                    "version": m.version,
                    "installed_at": m.installed_at.isoformat(),
                    "source": m.source,
                    "file_path": m.file_path,
                    "latest_version": m.latest_version,
                    "upgrade_available": m.upgrade_available
                }
                for name, m in self.modules.items()
            },
            "pending_upgrades": {
                uid: {
                    "module_name": r.module_name,
                    "current_version": r.current_version,
                    "new_version": r.new_version,
                    "requested_at": r.requested_at.isoformat(),
                    "confirmed": r.confirmed,
                    "confirmed_by": r.confirmed_by
                }
                for uid, r in self.pending_upgrades.items()
            }
        }
        
        state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def get_status(self) -> Dict:
        return {
            "status": self.status.value,
            "core_version": self.CORE_VERSION,
            "modules_count": len(self.modules),
            "pending_upgrades": len(self.pending_upgrades),
            "running": self._running
        }
    
    def get_modules(self) -> List[Dict]:
        return [
            {
                "name": m.name,
                "version": m.version,
                "source": m.source,
                "upgrade_available": m.upgrade_available,
                "latest_version": m.latest_version
            }
            for m in self.modules.values()
        ]
