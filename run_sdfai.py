#!/usr/bin/env python3
"""
SDFAI - SDF.org AI Assistant System
Main entry point with full Core module integration
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/sdfai.log')
    ]
)
logger = logging.getLogger('sdfai')

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "sdfai_config.json"
DATA_DIR = BASE_DIR / "data"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    return {}


class SDFAI:
    def __init__(self, config: dict):
        self.config = config
        self.im_gateway = None
        self.sdf_client = None
        self.llm_gateway = None
        self.supervisor_gateway = None  # 监督LLM
        self._running = False
        
        # Core模块
        self.message_queue = None
        self.message_router = None
        self.memory_manager = None
        self.security_evaluator = None
        
        # 数据目录
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "queues").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "memory").mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        logger.info("Initializing SDFAI...")
        
        # 初始化消息队列
        try:
            from core.message_queue import QueueManager, MessagePriority
            self.queue_manager = QueueManager(DATA_DIR / "queues")
            await self.queue_manager.start_all()
            logger.info("✅ 消息队列已启动")
        except Exception as e:
            logger.warning(f"消息队列初始化失败: {e}")
        
        # 初始化记忆管理
        try:
            from core.memory import MemoryManager
            self.memory_manager = MemoryManager(DATA_DIR / "memory")
            logger.info("✅ 记忆管理已启动")
        except Exception as e:
            logger.warning(f"记忆管理初始化失败: {e}")
        
        # 初始化IM Gateway
        from im_gateway import UnifiedIMGateway
        self.im_gateway = UnifiedIMGateway(self.config)
        self.im_gateway.set_message_handler(self._handle_message)
        await self.im_gateway.initialize()
        
        # 初始化SDF Client
        sdf_config = self.config.get("sdf", {})
        if sdf_config.get("enabled", False):
            from sdf_client import SDFClient
            self.sdf_client = SDFClient(
                host=sdf_config.get("host", "sdf.org"),
                port=sdf_config.get("port", 22)
            )
            await self.sdf_client.connect(
                username=sdf_config.get("username", ""),
                password=sdf_config.get("password", "")
            )
            await self.sdf_client.enter_com(sdf_config.get("room", "lobby"))
            
            # 设置COM消息回调并启动监听
            if hasattr(self.sdf_client, '_connection') and self.sdf_client._connection:
                self.sdf_client._connection.set_message_callback(self._handle_com_message)
                await self.sdf_client._connection.start_monitor()
                logger.info("✅ COM消息监听已启动")
            
            logger.info("✅ SDF COM聊天已连接")
        
        # 初始化LLM Gateway
        from xunfei_gateway import XunfeiGateway, XunfeiConfig
        llm_config = self.config.get("llm", {}).get(self.config.get("primary_llm", "xunfei-kimi"), {})
        
        if llm_config.get("enabled", True):
            self.llm_gateway = XunfeiGateway(XunfeiConfig(
                model_name=llm_config.get("model_name", "Kimi-K2-5"),
                model_id=llm_config.get("model_id", "xopkimik25"),
                app_id=llm_config.get("app_id", ""),
                api_key=llm_config.get("api_key", ""),
                api_secret=llm_config.get("api_secret", "")
            ))
            logger.info("✅ LLM已连接")
        
        # 初始化监督LLM (Qwen) - 作为备用和监督
        supervisor_config = self.config.get("llm", {}).get("supervisor", {})
        if supervisor_config.get("enabled", True):
            from qwen_gateway import QwenGateway, QwenConfig
            self.supervisor_gateway = QwenGateway(QwenConfig(
                model_id=supervisor_config.get("model_id", "xop3qwen1b7"),
                app_id=supervisor_config.get("app_id", ""),
                api_key=supervisor_config.get("api_key", ""),
                api_secret=supervisor_config.get("api_secret", "")
            ))
            logger.info("✅ 监督LLM已连接")
            
            # 初始化故障转移管理器
            from llm_failover import LLMFailoverManager
            self.llm_failover = LLMFailoverManager(
                primary_llm=self.llm_gateway,
                fallback_llm=self.supervisor_gateway
            )
            logger.info("✅ LLM故障转移已启用")
        
        # 初始化AI幻觉监督器
        from supervisor import init_supervisor
        self.hallucination_supervisor = await init_supervisor()
        
        logger.info("SDFAI initialized successfully")
        self._running = True
    
    async def _handle_com_message(self, message: str):
        """处理来自COM聊天室的消息"""
        logger.info(f"COM消息: {message[:100]}...")
        
        # 存入消息队列
        if self.queue_manager:
            from core.message_queue import QueueMessage, MessagePriority
            try:
                queue_msg = QueueMessage(
                    id=f"com_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    content=message,
                    source="sdf_com",
                    priority=MessagePriority.NORMAL,
                    metadata={"type": "com_message"}
                )
                await self.queue_manager.enqueue("incoming", queue_msg)
            except Exception as e:
                logger.error(f"消息入队失败: {e}")
        
        # 发送给LLM处理
        if self.llm_gateway:
            try:
                system_prompt = f"""你是SDFAI助手，正在监听SDF.org COM聊天室。

当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
当前房间: {self.sdf_client.current_room if self.sdf_client else 'unknown'}

请简洁地总结或回复这条消息。如果是普通聊天，可以忽略或简短回应。"""
                
                response = await self.llm_gateway.chat(
                    f"[COM消息] {message}",
                    system_prompt=system_prompt,
                    include_history=False
                )
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # 如果消息包含@yupeng或重要内容，转发到飞书
                if 'yupeng' in message.lower() or 'ai' in message.lower():
                    await self.im_gateway.send_message(
                        type('Platform', (), {'value': 'feishu'})(),
                        "default",
                        f"📢 COM消息:\n{message[:200]}\n\n🤖 AI回复: {response_text[:200]}"
                    )
            except Exception as e:
                logger.error(f"LLM处理COM消息失败: {e}")
    
    async def _handle_message(self, msg):
        """处理来自IM的消息"""
        logger.info(f"Received message from {msg.platform.value}: {msg.content[:50]}...")
        
        content = msg.content.strip()
        
        # AI幻觉防范：记录所有操作
        operation_result = None
        
        if content.startswith("com:"):
            message = content[4:].strip()
            if self.sdf_client:
                success = await self.sdf_client.send_com_message(message)
                operation_result = "success" if success else "failed"
                if success:
                    await self.im_gateway.send_message(
                        msg.platform, 
                        msg.chat_id, 
                        f"✅ COM消息已发送: {message[:30]}..."
                    )
                else:
                    await self.im_gateway.send_message(
                        msg.platform, 
                        msg.chat_id, 
                        f"❌ COM消息发送失败"
                    )
            else:
                operation_result = "no_client"
                await self.im_gateway.send_message(
                    msg.platform, 
                    msg.chat_id, 
                    "❌ SDF客户端未启用"
                )
        
        elif content.startswith("sh:"):
            command = content[3:].strip()
            if self.sdf_client:
                result = await self.sdf_client.execute_command(command)
                operation_result = "success" if result else "failed"
                if result:
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        f"执行结果:\n{result[:500]}"
                    )
                else:
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        f"❌ 命令执行失败: {command}"
                    )
            else:
                operation_result = "no_client"
                await self.im_gateway.send_message(
                    msg.platform, 
                    msg.chat_id, 
                    "❌ SDF客户端未启用"
                )
        
        elif content.startswith("g:"):
            room = content[2:].strip()
            if self.sdf_client:
                success = await self.sdf_client.switch_room(room)
                operation_result = "success" if success else "failed"
                if success:
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        f"✅ 已切换到房间: {room}"
                    )
                else:
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        f"❌ 切换房间失败: {room}"
                    )
            else:
                operation_result = "no_client"
                await self.im_gateway.send_message(
                    msg.platform,
                    msg.chat_id,
                    "❌ SDF客户端未启用"
                )
        
        elif content.startswith("s:"):
            parts = content[2:].strip().split(None, 1)
            if len(parts) >= 2:
                user, message = parts[0], parts[1]
                if self.sdf_client:
                    success = await self.sdf_client.send_private(user, message)
                    operation_result = "success" if success else "failed"
                    if success:
                        await self.im_gateway.send_message(
                            msg.platform,
                            msg.chat_id,
                            f"✅ 私聊已发送给 {user}"
                        )
                    else:
                        await self.im_gateway.send_message(
                            msg.platform,
                            msg.chat_id,
                            f"❌ 私聊发送失败: {user}"
                        )
                else:
                    operation_result = "no_client"
                    await self.im_gateway.send_message(
                        msg.platform, 
                        msg.chat_id, 
                        "❌ SDF客户端未启用"
                    )
        
        else:
            # LLM处理
            if self.llm_gateway:
                try:
                    # 使用system_prompts模块获取系统提示词
                    from system_prompts import get_main_llm_system_prompt
                    system_prompt = get_main_llm_system_prompt(
                        username=self.config.get('sdf', {}).get('username', 'unknown'),
                        current_room=self.sdf_client.current_room if self.sdf_client else 'lobby',
                        config=self.config
                    )
                    
                    response = await self.llm_gateway.chat(
                        content, 
                        system_prompt=system_prompt,
                        include_history=True
                    )
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    operation_result = "llm_success"
                    
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        response_text
                    )
                except Exception as e:
                    logger.error(f"LLM error: {e}")
                    operation_result = f"llm_error: {str(e)[:50]}"
                    await self.im_gateway.send_message(
                        msg.platform,
                        msg.chat_id,
                        f"LLM处理失败: {str(e)[:100]}"
                    )
        
        # 记录操作结果（AI幻觉防范）
        logger.info(f"Operation result: {operation_result}")
        
        # 存储到记忆
        if self.memory_manager:
            try:
                await self.memory_manager.store(
                    key=f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    content=content,
                    metadata={"result": operation_result, "platform": msg.platform.value}
                )
            except Exception as e:
                logger.warning(f"记忆存储失败: {e}")
    
    async def run(self):
        await self.initialize()
        
        logger.info("SDFAI started successfully")
        
        while self._running:
            await asyncio.sleep(1)
    
    async def shutdown(self):
        self._running = False
        
        if self.queue_manager:
            await self.queue_manager.stop_all()
        
        if self.im_gateway:
            await self.im_gateway.stop_all()
        
        if self.sdf_client:
            await self.sdf_client.disconnect()
        
        logger.info("SDFAI shutdown complete")


async def main():
    config = load_config()
    sdfai = SDFAI(config)
    
    try:
        await sdfai.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await sdfai.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
