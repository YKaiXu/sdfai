"""
Message Router - 消息路由器
硬编码路由规则，不可被LLM修改
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RouteType(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class MessageSource(Enum):
    SDF_COM = "sdf_com"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SKILL = "skill"
    INTERNAL = "internal"


class MessageTarget(Enum):
    SDF_COM = "sdf_com"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SKILL = "skill"
    ALL_IM = "all_im"


HARDCODED_ROUTING_RULES = {
    "COM_TO_IM": {
        "source": MessageSource.SDF_COM,
        "flow": ["ncurses_parse", "message_queue", "sdfai_core", "llm_process", "message_queue", "target_im"],
        "description": "COM消息经由NCurses解析后传送到消息队列，到SDFAI LLM，再发送到对应IM",
        "modifiable": False
    },
    "IM_TO_COM": {
        "source": MessageSource.FEISHU,
        "flow": ["message_queue", "sdfai_core", "llm_process", "message_queue", "sdf_com"],
        "description": "IM消息经由消息队列到SDFAI LLM，再发送到COM",
        "modifiable": False
    },
    "SKILL_TO_QUEUE": {
        "source": MessageSource.SKILL,
        "flow": ["standard_interface", "message_queue", "sdfai_core"],
        "description": "Skill消息通过标准接口进入消息队列",
        "modifiable": False
    }
}


@dataclass
class RoutedMessage:
    message_id: str
    source: MessageSource
    target: MessageTarget
    content: str
    route_type: RouteType
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    """
    消息路由器 - 硬编码路由规则
    所有路由逻辑在此定义，不可被LLM修改
    """
    
    HARDCODED_FLOWS = {
        (MessageSource.SDF_COM, RouteType.INBOUND): [
            "ncurses_parse",
            "message_queue_in",
            "sdfai_core",
            "llm_process",
            "message_queue_out",
            "target_im"
        ],
        (MessageSource.FEISHU, RouteType.INBOUND): [
            "message_queue_in",
            "sdfai_core",
            "llm_process",
            "message_queue_out",
            "sdf_com"
        ],
        (MessageSource.SKILL, RouteType.INBOUND): [
            "standard_interface",
            "message_queue_in",
            "sdfai_core"
        ]
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._handlers: Dict[str, Callable] = {}
        self._route_history: List[Dict] = []
    
    def get_route_flow(self, source: MessageSource, route_type: RouteType) -> List[str]:
        return self.HARDCODED_FLOWS.get((source, route_type), [])
    
    def validate_route(self, source: MessageSource, target: MessageTarget) -> bool:
        valid_routes = [
            (MessageSource.SDF_COM, MessageTarget.FEISHU),
            (MessageSource.SDF_COM, MessageTarget.DINGTALK),
            (MessageSource.SDF_COM, MessageTarget.ALL_IM),
            (MessageSource.FEISHU, MessageTarget.SDF_COM),
            (MessageSource.DINGTALK, MessageTarget.SDF_COM),
            (MessageSource.SKILL, MessageTarget.ALL_IM),
        ]
        return (source, target) in valid_routes
    
    def register_handler(self, flow_step: str, handler: Callable):
        self._handlers[flow_step] = handler
    
    async def route(self, message: RoutedMessage) -> bool:
        flow = self.get_route_flow(message.source, message.route_type)
        
        if not flow:
            return False
        
        for step in flow:
            if step in self._handlers:
                handler = self._handlers[step]
                try:
                    if asyncio.iscoroutinefunction(handler):
                        message = await handler(message)
                    else:
                        message = handler(message)
                except Exception as e:
                    self._log_route_error(message, step, str(e))
                    return False
        
        message.processed = True
        self._log_route_success(message, flow)
        return True
    
    def _log_route_success(self, message: RoutedMessage, flow: List[str]):
        self._route_history.append({
            "message_id": message.message_id,
            "source": message.source.value,
            "target": message.target.value,
            "flow": flow,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })
        self._save_history()
    
    def _log_route_error(self, message: RoutedMessage, step: str, error: str):
        self._route_history.append({
            "message_id": message.message_id,
            "source": message.source.value,
            "step": step,
            "error": error,
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        })
        self._save_history()
    
    def _save_history(self):
        history_file = self.data_dir / "route_history.json"
        history_file.write_text(
            json.dumps(self._route_history[-100:], ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def get_routing_rules(self) -> Dict:
        return {
            "hardcoded_rules": HARDCODED_ROUTING_RULES,
            "modifiable": False,
            "warning": "These routing rules are hardcoded and cannot be modified by LLM"
        }


import asyncio
