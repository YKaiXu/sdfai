#!/usr/bin/env python3
"""
Qwen Gateway - 监督LLM网关
用于AI幻觉防范
"""
import asyncio
import json
import hmac
import hashlib
import base64
from datetime import datetime
from urllib.parse import urlencode, urlparse
import websockets
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger('qwen_gateway')


@dataclass
class QwenConfig:
    model_id: str = "xop3qwen1b7"
    app_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    ws_url: str = "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat"


@dataclass
class SupervisionResult:
    is_valid: bool
    issues: List[str]
    confidence: float
    recommendation: str


class QwenGateway:
    def __init__(self, config: QwenConfig):
        self.config = config
        self._ws = None
    
    def _create_auth_url(self) -> str:
        host = urlparse(self.config.ws_url).netloc
        path = urlparse(self.config.ws_url).path
        
        now = datetime.utcnow()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.config.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode('utf-8')
        
        authorization_origin = f'api_key="{self.config.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        params = {"authorization": authorization, "date": date, "host": host}
        return f"{self.config.ws_url}?{urlencode(params)}"
    
    async def _connect(self):
        if self._ws and not self._ws.closed:
            return
        
        url = self._create_auth_url()
        self._ws = await websockets.connect(url)
    
    async def supervise(self, operation: str, input_data: str, output_data: str, actual_result: str = None) -> SupervisionResult:
        prompt = f"""你是AI输出监督员。检查以下操作是否存在幻觉问题。

操作类型: {operation}
用户输入: {input_data}
AI输出: {output_data}
实际结果: {actual_result or "未提供"}

检查项目：
1. AI是否声称执行了未实际执行的操作？
2. AI输出是否与实际结果矛盾？
3. AI是否编造了不存在的信息？

请用JSON格式回复：
{{"is_valid": true/false, "issues": ["问题列表"], "confidence": 0.0-1.0, "recommendation": "建议"}}"""

        try:
            await self._connect()
            
            req = {
                "header": {"app_id": self.config.app_id},
                "parameter": {"chat": {"domain": self.config.model_id}},
                "payload": {"message": {"text": [{"role": "user", "content": prompt}]}}
            }
            
            await self._ws.send(json.dumps(req))
            
            result_text = ""
            while True:
                try:
                    msg = await asyncio.wait_for(self._ws.recv(), timeout=30)
                    data = json.loads(msg)
                    if data.get("header", {}).get("code") != 0:
                        logger.error(f"Qwen API error: {data}")
                        break
                    content = data.get("payload", {}).get("choices", {}).get("text", [])
                    for item in content:
                        result_text += item.get("content", "")
                    if data.get("header", {}).get("status") == 2:
                        break
                except asyncio.TimeoutError:
                    break
            
            # 解析JSON
            import re
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return SupervisionResult(
                    is_valid=result.get("is_valid", True),
                    issues=result.get("issues", []),
                    confidence=result.get("confidence", 0.5),
                    recommendation=result.get("recommendation", "")
                )
            
            return SupervisionResult(is_valid=True, issues=[], confidence=0.5, recommendation="无法解析监督结果")
            
        except Exception as e:
            logger.error(f"Supervision error: {e}")
            return SupervisionResult(is_valid=True, issues=[f"监督失败: {str(e)}"], confidence=0.0, recommendation="监督服务异常")
    
    async def close(self):
        if self._ws:
            await self._ws.close()
