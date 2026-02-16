#!/usr/bin/env python3
"""
Unified IM Gateway for SDFAI
Based on nanobot implementations - no public IP required

Supported platforms:
- Feishu (飞书) - WebSocket via lark-oapi SDK (multiprocessing)
- DingTalk (钉钉) - Stream Mode via dingtalk-stream SDK
- QQ - WebSocket via qq-botpy SDK
"""
import asyncio
import json
import logging
import subprocess
import sys
import time
import os
from collections import OrderedDict
from typing import Any, Optional, Callable, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IMPlatform(Enum):
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    QQ = "qq"


@dataclass
class IMMessage:
    platform: IMPlatform
    sender_id: str
    chat_id: str
    content: str
    sender_name: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseIMChannel:
    """Base class for IM channels"""
    
    name = "base"
    
    def __init__(self, config: dict, message_handler: Callable):
        self.config = config
        self.message_handler = message_handler
        self._running = False
        self._processed_ids = OrderedDict()
    
    async def start(self) -> bool:
        raise NotImplementedError
    
    async def stop(self):
        self._running = False
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        raise NotImplementedError
    
    def _is_processed(self, msg_id: str) -> bool:
        if msg_id in self._processed_ids:
            return True
        self._processed_ids[msg_id] = None
        while len(self._processed_ids) > 1000:
            self._processed_ids.popitem(last=False)
        return False


try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    lark = None


class FeishuChannel(BaseIMChannel):
    """Feishu channel using WebSocket via subprocess"""
    
    name = "feishu"
    
    def __init__(self, config: dict, message_handler: Callable):
        super().__init__(config, message_handler)
        self._client: Any = None
        self._process: Optional[subprocess.Popen] = None
        self._poll_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        if not FEISHU_AVAILABLE:
            logger.error("lark-oapi SDK not installed. Run: pip install lark-oapi")
            return False
        
        app_id = self.config.get("app_id")
        app_secret = self.config.get("app_secret")
        
        if not app_id or not app_secret:
            logger.error("Feishu app_id and app_secret not configured")
            return False
        
        self._running = True
        
        logger.info(f"Initializing Feishu client with app_id: {app_id[:10]}...")
        
        self._client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        script_path = os.path.join(os.path.dirname(__file__), "feishu_ws_subprocess.py")
        
        if not os.path.exists(script_path):
            logger.error(f"Feishu subprocess script not found: {script_path}")
            return False
        
        self._process = subprocess.Popen(
            [
                sys.executable, script_path,
                app_id, app_secret,
                self.config.get("encrypt_key", ""),
                self.config.get("verification_token", "")
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        self._poll_task = asyncio.create_task(self._poll_messages())
        
        logger.info("Feishu WebSocket started via subprocess")
        return True
    
    async def _poll_messages(self):
        """Poll messages from the WebSocket subprocess"""
        import sys
        
        while self._running and self._process:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self._process.stdout.readline
                )
                
                if not line:
                    if self._process.poll() is not None:
                        logger.warning("Feishu subprocess ended, restarting...")
                        await self._restart_process()
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                if msg.get("type") == "message":
                    if self._is_processed(msg.get("message_id", "")):
                        continue
                    
                    await self.message_handler(IMMessage(
                        platform=IMPlatform.FEISHU,
                        sender_id=msg.get("sender_id", ""),
                        chat_id=msg.get("chat_id", ""),
                        content=msg.get("content", ""),
                        metadata={"message_id": msg.get("message_id", "")}
                    ))
                elif msg.get("type") == "status":
                    logger.info(f"Feishu WebSocket: {msg.get('status')}")
                elif msg.get("type") == "error":
                    logger.warning(f"Feishu WebSocket error: {msg.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error polling Feishu messages: {e}")
                await asyncio.sleep(1)
    
    async def _restart_process(self):
        """Restart the Feishu subprocess"""
        if self._process:
            self._process.terminate()
            self._process.wait()
        
        app_id = self.config.get("app_id")
        app_secret = self.config.get("app_secret")
        script_path = os.path.join(os.path.dirname(__file__), "feishu_ws_subprocess.py")
        
        self._process = subprocess.Popen(
            [
                sys.executable, script_path,
                app_id, app_secret,
                self.config.get("encrypt_key", ""),
                self.config.get("verification_token", "")
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    
    async def stop(self):
        await super().stop()
        if self._poll_task:
            self._poll_task.cancel()
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=2)
        logger.info("Feishu stopped")
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        if not self._client:
            logger.warning("Feishu client not initialized")
            return False
        
        try:
            receive_id_type = "chat_id" if chat_id.startswith("oc_") else "open_id"
            
            card = {
                "config": {"wide_screen_mode": True},
                "elements": [{"tag": "markdown", "content": text}]
            }
            content = json.dumps(card, ensure_ascii=False)
            
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("interactive")
                    .content(content)
                    .build()
                ).build()
            
            response = self._client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"Failed to send: code={response.code}, msg={response.msg}")
                return False
            
            logger.info(f"Feishu message sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Feishu message: {e}")
            return False


try:
    from dingtalk_stream import DingTalkStreamClient, Credential, CallbackHandler, CallbackMessage, AckMessage
    from dingtalk_stream.chatbot import ChatbotMessage
    import httpx
    DINGTALK_AVAILABLE = True
except ImportError:
    DINGTALK_AVAILABLE = False


class DingTalkChannel(BaseIMChannel):
    """DingTalk channel using Stream Mode"""
    
    name = "dingtalk"
    
    def __init__(self, config: dict, message_handler: Callable):
        super().__init__(config, message_handler)
        self._client: Any = None
        self._http: Any = None
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        self._background_tasks: set = set()
    
    async def start(self) -> bool:
        if not DINGTALK_AVAILABLE:
            logger.error("dingtalk-stream SDK not installed. Run: pip install dingtalk-stream")
            return False
        
        client_id = self.config.get("client_id") or self.config.get("app_key")
        client_secret = self.config.get("client_secret") or self.config.get("app_secret")
        
        if not client_id or not client_secret:
            logger.error("DingTalk client_id and client_secret not configured")
            return False
        
        self._running = True
        self._http = httpx.AsyncClient()
        
        logger.info(f"Initializing DingTalk Stream Client...")
        
        credential = Credential(client_id, client_secret)
        self._client = DingTalkStreamClient(credential)
        
        channel = self
        
        class Handler(CallbackHandler):
            async def process(self, message: CallbackMessage):
                try:
                    chatbot_msg = ChatbotMessage.from_dict(message.data)
                    content = ""
                    if chatbot_msg.text:
                        content = chatbot_msg.text.content.strip()
                    if not content:
                        content = message.data.get("text", {}).get("content", "").strip()
                    
                    if not content:
                        return AckMessage.STATUS_OK, "OK"
                    
                    sender_id = chatbot_msg.sender_staff_id or chatbot_msg.sender_id
                    sender_name = chatbot_msg.sender_nick or "Unknown"
                    
                    task = asyncio.create_task(
                        channel.message_handler(IMMessage(
                            platform=IMPlatform.DINGTALK,
                            sender_id=sender_id,
                            chat_id=sender_id,
                            content=content,
                            sender_name=sender_name
                        ))
                    )
                    channel._background_tasks.add(task)
                    task.add_done_callback(channel._background_tasks.discard)
                    
                    return AckMessage.STATUS_OK, "OK"
                except Exception as e:
                    return AckMessage.STATUS_OK, "Error"
        
        self._client.register_callback_handler(ChatbotMessage.TOPIC, Handler())
        
        asyncio.create_task(self._run_stream())
        logger.info("DingTalk bot started with Stream Mode")
        return True
    
    async def _run_stream(self):
        while self._running:
            try:
                await self._client.start()
            except Exception as e:
                logger.warning(f"DingTalk stream error: {e}")
            if self._running:
                await asyncio.sleep(5)
    
    async def stop(self):
        await super().stop()
        if self._http:
            await self._http.aclose()
        for task in self._background_tasks:
            task.cancel()
        logger.info("DingTalk stopped")
    
    async def _get_access_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        
        client_id = self.config.get("client_id") or self.config.get("app_key")
        client_secret = self.config.get("client_secret") or self.config.get("app_secret")
        
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        data = {"appKey": client_id, "appSecret": client_secret}
        
        try:
            resp = await self._http.post(url, json=data)
            resp.raise_for_status()
            res_data = resp.json()
            self._access_token = res_data.get("accessToken")
            self._token_expiry = time.time() + int(res_data.get("expireIn", 7200)) - 60
            return self._access_token
        except Exception as e:
            logger.error(f"Failed to get DingTalk access token: {e}")
            return None
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        token = await self._get_access_token()
        if not token:
            return False
        
        client_id = self.config.get("client_id") or self.config.get("app_key")
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        headers = {"x-acs-dingtalk-access-token": token}
        data = {
            "robotCode": client_id,
            "userIds": [chat_id],
            "msgKey": "sampleMarkdown",
            "msgParam": json.dumps({"text": text, "title": "SDFAI Reply"})
        }
        
        try:
            resp = await self._http.post(url, json=data, headers=headers)
            if resp.status_code != 200:
                logger.error(f"DingTalk send failed: {resp.text}")
                return False
            logger.info(f"DingTalk message sent to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending DingTalk message: {e}")
            return False


try:
    import botpy
    from botpy.message import C2CMessage
    QQ_AVAILABLE = True
except ImportError:
    QQ_AVAILABLE = False


class QQChannel(BaseIMChannel):
    """QQ channel using botpy SDK"""
    
    name = "qq"
    
    def __init__(self, config: dict, message_handler: Callable):
        super().__init__(config, message_handler)
        self._client: Any = None
        self._bot_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        if not QQ_AVAILABLE:
            logger.error("qq-botpy SDK not installed. Run: pip install qq-botpy")
            return False
        
        app_id = self.config.get("app_id")
        secret = self.config.get("secret")
        
        if not app_id or not secret:
            logger.error("QQ app_id and secret not configured")
            return False
        
        self._running = True
        
        channel = self
        intents = botpy.Intents(public_messages=True, direct_message=True)
        
        class Bot(botpy.Client):
            async def on_ready(self):
                logger.info(f"QQ bot ready: {self.robot.name}")
            
            async def on_c2c_message_create(self, message: C2CMessage):
                await channel._on_message(message)
            
            async def on_direct_message_create(self, message):
                await channel._on_message(message)
        
        self._client = Bot(intents=intents)
        self._bot_task = asyncio.create_task(self._run_bot())
        
        logger.info("QQ bot started")
        return True
    
    async def _run_bot(self):
        while self._running:
            try:
                await self._client.start(
                    appid=self.config.get("app_id"),
                    secret=self.config.get("secret")
                )
            except Exception as e:
                logger.warning(f"QQ bot error: {e}")
            if self._running:
                await asyncio.sleep(5)
    
    async def stop(self):
        await super().stop()
        if self._bot_task:
            self._bot_task.cancel()
        logger.info("QQ stopped")
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        if not self._client:
            return False
        try:
            await self._client.api.post_c2c_message(
                openid=chat_id,
                msg_type=0,
                content=text
            )
            logger.info(f"QQ message sent to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending QQ message: {e}")
            return False
    
    async def _on_message(self, data: C2CMessage):
        try:
            if self._is_processed(data.id):
                return
            
            author = data.author
            user_id = str(getattr(author, 'id', None) or getattr(author, 'user_openid', 'unknown'))
            content = (data.content or "").strip()
            
            if not content:
                return
            
            await self.message_handler(IMMessage(
                platform=IMPlatform.QQ,
                sender_id=user_id,
                chat_id=user_id,
                content=content,
                metadata={"message_id": data.id}
            ))
        except Exception as e:
            logger.error(f"Error handling QQ message: {e}")


class UnifiedIMGateway:
    """Unified IM Gateway Manager"""
    
    def __init__(self, config: dict):
        self.config = config
        self.channels: Dict[IMPlatform, BaseIMChannel] = {}
        self._message_handler: Optional[Callable] = None
    
    def set_message_handler(self, handler: Callable):
        self._message_handler = handler
    
    async def initialize(self) -> Dict[str, bool]:
        """Initialize all enabled IM platforms"""
        results = {}
        im_config = self.config.get("im", {})
        
        if im_config.get("feishu", {}).get("enabled"):
            channel = FeishuChannel(im_config["feishu"], self._handle_message)
            success = await channel.start()
            if success:
                self.channels[IMPlatform.FEISHU] = channel
            results["feishu"] = success
        
        if im_config.get("dingtalk", {}).get("enabled"):
            channel = DingTalkChannel(im_config["dingtalk"], self._handle_message)
            success = await channel.start()
            if success:
                self.channels[IMPlatform.DINGTALK] = channel
            results["dingtalk"] = success
        
        if im_config.get("qq", {}).get("enabled"):
            channel = QQChannel(im_config["qq"], self._handle_message)
            success = await channel.start()
            if success:
                self.channels[IMPlatform.QQ] = channel
            results["qq"] = success
        
        return results
    
    async def _handle_message(self, msg: IMMessage):
        if self._message_handler:
            await self._message_handler(msg)
    
    async def send_message(self, platform: IMPlatform, chat_id: str, text: str) -> bool:
        channel = self.channels.get(platform)
        if channel:
            return await channel.send_message(chat_id, text)
        return False
    
    async def stop_all(self):
        for channel in self.channels.values():
            await channel.stop()
        self.channels.clear()
    
    @staticmethod
    def get_required_packages() -> Dict[str, str]:
        return {
            "feishu": "pip install lark-oapi",
            "dingtalk": "pip install dingtalk-stream",
            "qq": "pip install qq-botpy"
        }
