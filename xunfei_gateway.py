#!/usr/bin/env python3
"""
Xunfei LLM Gateway for sdfai
Supports Xunfei Spark/Kimi models via WebSocket API
"""
import asyncio
import hashlib
import hmac
import base64
import json
import time
import uuid
import websockets
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import urllib.parse
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XunfeiModel(Enum):
    SPARK_V1 = "spark-v1"
    SPARK_V2 = "spark-v2"
    SPARK_V3 = "spark-v3"
    SPARK_V35 = "spark-v3.5"
    SPARK_V4 = "spark-v4"
    KIMI_K2_5 = "xopkimik25"
    GENERAL_V1 = "generalv1"
    GENERAL_V2 = "generalv2"
    GENERAL_V3 = "generalv3"


@dataclass
class XunfeiConfig:
    model_name: str
    model_id: str
    app_id: str
    api_key: str
    api_secret: str
    ws_url: str = "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat"
    enabled: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class ChatMessage:
    role: str
    content: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw_response: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason
        }


class XunfeiGateway:
    def __init__(self, config: XunfeiConfig):
        self.config = config
        self._conversation_history: Dict[str, List[ChatMessage]] = {}
        
    def _generate_auth_url(self) -> str:
        host = urllib.parse.urlparse(self.config.ws_url).netloc
        path = urllib.parse.urlparse(self.config.ws_url).path
        
        date_rfc1123 = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        signature_origin = f"host: {host}\ndate: {date_rfc1123}\nGET {path} HTTP/1.1"
        
        signature_sha = hmac.new(
            self.config.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature = base64.b64encode(signature_sha).decode('utf-8')
        
        authorization_origin = f'api_key="{self.config.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        params = {
            "authorization": authorization,
            "date": date_rfc1123,
            "host": host
        }
        
        return f"{self.config.ws_url}?{urllib.parse.urlencode(params)}"
    
    def _build_request(self, messages: List[ChatMessage], stream: bool = True) -> Dict:
        uid = str(uuid.uuid4()).replace('-', '')[:32]
        
        return {
            "header": {
                "app_id": self.config.app_id,
                "uid": uid
            },
            "parameter": {
                "chat": {
                    "domain": self.config.model_id,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                }
            },
            "payload": {
                "message": {
                    "text": [m.to_dict() for m in messages]
                }
            }
        }
    
    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        conv_id = conversation_id or str(uuid.uuid4())
        if conv_id not in self._conversation_history:
            self._conversation_history[conv_id] = []
        return conv_id
    
    def add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self._conversation_history:
            self._conversation_history[conversation_id] = []
        
        self._conversation_history[conversation_id].append(
            ChatMessage(role=role, content=content)
        )
    
    def get_history(self, conversation_id: str) -> List[ChatMessage]:
        return self._conversation_history.get(conversation_id, [])
    
    def clear_history(self, conversation_id: str):
        if conversation_id in self._conversation_history:
            self._conversation_history[conversation_id] = []
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        include_history: bool = True
    ) -> LLMResponse:
        conv_id = conversation_id or self.create_conversation()
        
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        if include_history:
            messages.extend(self.get_history(conv_id))
        
        messages.append(ChatMessage(role="user", content=message))
        
        self.add_message(conv_id, "user", message)
        
        url = self._generate_auth_url()
        request = self._build_request(messages)
        
        full_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(request))
                
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=120)
                        data = json.loads(response)
                        
                        header = data.get("header", {})
                        code = header.get("code", 0)
                        
                        if code != 0:
                            error_msg = header.get("message", "Unknown error")
                            logger.error(f"API error: {code} - {error_msg}")
                            raise Exception(f"API error: {error_msg}")
                        
                        payload = data.get("payload", {})
                        choices = payload.get("choices", {})
                        text_list = choices.get("text", [])
                        
                        for text_item in text_list:
                            content = text_item.get("content", "")
                            full_content += content
                        
                        usage_data = payload.get("usage", {})
                        if usage_data:
                            usage = {
                                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                                "completion_tokens": usage_data.get("completion_tokens", 0),
                                "total_tokens": usage_data.get("total_tokens", 0)
                            }
                        
                        status = header.get("status", 0)
                        if status == 2:
                            break
                            
                    except asyncio.TimeoutError:
                        logger.error("WebSocket timeout")
                        raise Exception("WebSocket timeout")
        
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise
        
        self.add_message(conv_id, "assistant", full_content)
        
        return LLMResponse(
            content=full_content,
            model=self.config.model_name,
            usage=usage,
            finish_reason="stop",
            raw_response={}
        )
    
    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        include_history: bool = True
    ) -> AsyncGenerator[str, None]:
        conv_id = conversation_id or self.create_conversation()
        
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        if include_history:
            messages.extend(self.get_history(conv_id))
        
        messages.append(ChatMessage(role="user", content=message))
        
        self.add_message(conv_id, "user", message)
        
        url = self._generate_auth_url()
        request = self._build_request(messages)
        
        full_content = ""
        
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(request))
                
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=120)
                        data = json.loads(response)
                        
                        header = data.get("header", {})
                        code = header.get("code", 0)
                        
                        if code != 0:
                            error_msg = header.get("message", "Unknown error")
                            logger.error(f"API error: {code} - {error_msg}")
                            raise Exception(f"API error: {error_msg}")
                        
                        payload = data.get("payload", {})
                        choices = payload.get("choices", {})
                        text_list = choices.get("text", [])
                        
                        for text_item in text_list:
                            content = text_item.get("content", "")
                            if content:
                                full_content += content
                                yield content
                        
                        status = header.get("status", 0)
                        if status == 2:
                            break
                            
                    except asyncio.TimeoutError:
                        logger.error("WebSocket timeout")
                        raise Exception("WebSocket timeout")
        
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            raise
        
        self.add_message(conv_id, "assistant", full_content)
    
    async def single_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        messages.append(ChatMessage(role="user", content=message))
        
        url = self._generate_auth_url()
        request = self._build_request(messages)
        
        full_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(request))
                
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=120)
                        data = json.loads(response)
                        
                        header = data.get("header", {})
                        code = header.get("code", 0)
                        
                        if code != 0:
                            error_msg = header.get("message", "Unknown error")
                            logger.error(f"API error: {code} - {error_msg}")
                            raise Exception(f"API error: {error_msg}")
                        
                        payload = data.get("payload", {})
                        choices = payload.get("choices", {})
                        text_list = choices.get("text", [])
                        
                        for text_item in text_list:
                            content = text_item.get("content", "")
                            full_content += content
                        
                        usage_data = payload.get("usage", {})
                        if usage_data:
                            usage = {
                                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                                "completion_tokens": usage_data.get("completion_tokens", 0),
                                "total_tokens": usage_data.get("total_tokens", 0)
                            }
                        
                        status = header.get("status", 0)
                        if status == 2:
                            break
                            
                    except asyncio.TimeoutError:
                        logger.error("WebSocket timeout")
                        raise Exception("WebSocket timeout")
        
        except Exception as e:
            logger.error(f"Error in single chat: {e}")
            raise
        
        return LLMResponse(
            content=full_content,
            model=self.config.model_name,
            usage=usage,
            finish_reason="stop",
            raw_response={}
        )
    
    async def test_connection(self) -> bool:
        try:
            response = await self.single_chat("Hello, please respond with 'OK' to confirm connection.")
            logger.info(f"Connection test successful: {response.content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


async def create_xunfei_gateway(config: Dict) -> XunfeiGateway:
    xunfei_config = XunfeiConfig(
        model_name=config.get("model_name", "Kimi-K2-5"),
        model_id=config.get("model_id", "xopkimik25"),
        app_id=config.get("app_id", ""),
        api_key=config.get("api_key", ""),
        api_secret=config.get("api_secret", ""),
        ws_url=config.get("ws_url", "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat"),
        enabled=config.get("enabled", True),
        max_tokens=config.get("max_tokens", 4096),
        temperature=config.get("temperature", 0.7)
    )
    return XunfeiGateway(xunfei_config)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        config = {
            "model_name": "Kimi-K2-5",
            "model_id": "xopkimik25",
            "app_id": "b75e516d",
            "api_key": "a943e63a5fbded921da23a3328d5bfeb",
            "api_secret": "MmRkNWZhYWEwZTk5NGMyNzA3NmExZTAz",
            "ws_url": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat",
            "enabled": True
        }
        
        gateway = await create_xunfei_gateway(config)
        
        print("Testing Xunfei Kimi WebSocket connection...")
        success = await gateway.test_connection()
        
        if success:
            print("Xunfei Kimi gateway configured successfully!")
        else:
            print("Failed to connect to Xunfei Kimi")
    
    asyncio.run(test())
