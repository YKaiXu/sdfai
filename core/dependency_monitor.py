"""
Dependency Monitor - Python依赖库升级监控
每隔7天轮询检查升级，通知用户确认后升级
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class UpgradeStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PackageInfo:
    name: str
    current_version: str
    latest_version: Optional[str] = None
    upgrade_available: bool = False
    description: str = ""
    last_checked: datetime = None


@dataclass
class UpgradeRequest:
    package_name: str
    current_version: str
    new_version: str
    requested_at: datetime
    status: UpgradeStatus = UpgradeStatus.PENDING
    confirmed_by: Optional[str] = None


class DependencyMonitor:
    CHECK_INTERVAL_DAYS = 7
    CRITICAL_PACKAGES = [
        "asyncssh",
        "aiohttp",
        "requests",
        "psutil",
        "watchdog",
    ]
    
    def __init__(self, data_dir: Path, im_notifier: Callable = None):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.im_notifier = im_notifier
        
        self.packages: Dict[str, PackageInfo] = {}
        self.pending_upgrades: Dict[str, UpgradeRequest] = {}
        self.last_check: Optional[datetime] = None
        
        self._load_state()
    
    async def check_all_packages(self) -> Dict:
        print("🔍 检查Python依赖包更新...")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {"error": result.stderr}
        
        try:
            installed = json.loads(result.stdout)
        except:
            return {"error": "Failed to parse pip list output"}
        
        for pkg in installed:
            name = pkg["name"].lower()
            version = pkg["version"]
            
            self.packages[name] = PackageInfo(
                name=name,
                current_version=version,
                last_checked=datetime.now()
            )
        
        await self._check_for_updates()
        
        self.last_check = datetime.now()
        await self._save_state()
        
        upgrades_available = [
            p.name for p in self.packages.values() 
            if p.upgrade_available
        ]
        
        if upgrades_available and self.im_notifier:
            await self._notify_upgrades(upgrades_available)
        
        return {
            "checked_at": self.last_check.isoformat(),
            "total_packages": len(self.packages),
            "upgrades_available": len(upgrades_available),
            "packages": upgrades_available
        }
    
    async def _check_for_updates(self):
        for name, pkg in self.packages.items():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "index", "versions", name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    import re
                    match = re.search(r'Available versions:\s*([\d.,\s]+)', result.stdout)
                    if match:
                        versions = [v.strip() for v in match.group(1).split(',')]
                        if versions:
                            latest = versions[0]
                            pkg.latest_version = latest
                            pkg.upgrade_available = latest != pkg.current_version
            except:
                pass
    
    async def _notify_upgrades(self, packages: List[str]):
        critical = [p for p in packages if p in self.CRITICAL_PACKAGES]
        other = [p for p in packages if p not in self.CRITICAL_PACKAGES]
        
        message = f"""
📦 Python依赖包更新可用

🔴 关键包更新 ({len(critical)}):
{chr(10).join(f'  - {p}: {self.packages[p].current_version} → {self.packages[p].latest_version}' for p in critical[:5])}

📦 其他包更新 ({len(other)}):
{chr(10).join(f'  - {p}' for p in other[:10])}

回复 "upgrade <包名>" 升级指定包
回复 "upgrade_all" 升级所有关键包
回复 "skip" 跳过此次更新
"""
        
        await self.im_notifier(message, {"type": "dependency_update"})
    
    async def request_upgrade(self, package_name: str) -> Optional[str]:
        pkg = self.packages.get(package_name.lower())
        if not pkg or not pkg.upgrade_available:
            return None
        
        upgrade_id = f"upgrade_{package_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self.pending_upgrades[upgrade_id] = UpgradeRequest(
            package_name=package_name,
            current_version=pkg.current_version,
            new_version=pkg.latest_version,
            requested_at=datetime.now()
        )
        
        await self._save_state()
        
        message = f"""
📦 升级确认请求

包名: {package_name}
当前版本: {pkg.current_version}
新版本: {pkg.latest_version}

回复 "confirm {upgrade_id}" 确认升级
回复 "reject {upgrade_id}" 取消
"""
        
        if self.im_notifier:
            await self.im_notifier(message, {"type": "upgrade_confirm", "upgrade_id": upgrade_id})
        
        return upgrade_id
    
    async def confirm_upgrade(self, upgrade_id: str, confirmed_by: str = "user") -> bool:
        if upgrade_id not in self.pending_upgrades:
            return False
        
        request = self.pending_upgrades[upgrade_id]
        request.status = UpgradeStatus.CONFIRMED
        request.confirmed_by = confirmed_by
        
        result = await self._execute_upgrade(request)
        
        return result
    
    async def _execute_upgrade(self, request: UpgradeRequest) -> bool:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", request.package_name],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                request.status = UpgradeStatus.COMPLETED
                
                if request.package_name.lower() in self.packages:
                    self.packages[request.package_name.lower()].current_version = request.new_version
                    self.packages[request.package_name.lower()].upgrade_available = False
                
                await self._save_state()
                
                if self.im_notifier:
                    await self.im_notifier(
                        f"✅ {request.package_name} 已升级到 {request.new_version}",
                        {"type": "upgrade_completed"}
                    )
                
                return True
            else:
                request.status = UpgradeStatus.FAILED
                
                if self.im_notifier:
                    await self.im_notifier(
                        f"❌ {request.package_name} 升级失败: {result.stderr[:100]}",
                        {"type": "upgrade_failed"}
                    )
                
                return False
                
        except Exception as e:
            request.status = UpgradeStatus.FAILED
            return False
    
    def should_check(self) -> bool:
        if not self.last_check:
            return True
        
        return datetime.now() - self.last_check >= timedelta(days=self.CHECK_INTERVAL_DAYS)
    
    async def start_periodic_check(self):
        while True:
            if self.should_check():
                await self.check_all_packages()
            
            await asyncio.sleep(3600)
    
    def _get_state_file(self) -> Path:
        return self.data_dir / "dependency_state.json"
    
    async def _save_state(self):
        state = {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "packages": {
                name: {
                    "current_version": p.current_version,
                    "latest_version": p.latest_version,
                    "upgrade_available": p.upgrade_available,
                    "last_checked": p.last_checked.isoformat() if p.last_checked else None
                }
                for name, p in self.packages.items()
            },
            "pending_upgrades": {
                uid: {
                    "package_name": r.package_name,
                    "current_version": r.current_version,
                    "new_version": r.new_version,
                    "status": r.status.value,
                    "requested_at": r.requested_at.isoformat()
                }
                for uid, r in self.pending_upgrades.items()
            }
        }
        
        self._get_state_file().write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def _load_state(self):
        state_file = self._get_state_file()
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding='utf-8'))
                
                if state.get("last_check"):
                    self.last_check = datetime.fromisoformat(state["last_check"])
                
                for name, data in state.get("packages", {}).items():
                    self.packages[name] = PackageInfo(
                        name=name,
                        current_version=data["current_version"],
                        latest_version=data.get("latest_version"),
                        upgrade_available=data.get("upgrade_available", False),
                        last_checked=datetime.fromisoformat(data["last_checked"]) if data.get("last_checked") else None
                    )
            except:
                pass
