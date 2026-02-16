# LLM 大语言模型模块

## 概述

SDFAI使用双LLM架构，主LLM负责对话，监督LLM负责幻觉检测和故障转移。

## 主LLM - Kimi-K2-5

### xunfei_gateway.py
- **功能**: 讯飞星火大模型接口
- **模型**: Kimi-K2-5
- **用途**: 主要对话处理
- **特点**: 高质量对话输出

### 配置
```json
{
  "llm": {
    "xunfei-kimi": {
      "model_name": "Kimi-K2-5",
      "model_id": "xopkimik25",
      "app_id": "...",
      "api_key": "...",
      "api_secret": "..."
    }
  }
}
```

## 监督LLM - Qwen3-1.7B

### qwen_gateway.py
- **功能**: Qwen大模型接口
- **模型**: Qwen3-1.7B
- **用途**: AI幻觉监督、故障转移备用
- **特点**: 免费稳定

### 配置
```json
{
  "llm": {
    "supervisor": {
      "model_name": "Qwen3-1.7B",
      "model_id": "xop3qwen1b7",
      "app_id": "...",
      "api_key": "...",
      "api_secret": "..."
    }
  }
}
```

## 故障转移

### llm_failover.py
- **功能**: LLM故障自动转移
- **机制**: 主LLM失败自动切换备用
- **恢复**: 定期尝试恢复主LLM

## 使用示例

```python
from xunfei_gateway import XunfeiGateway, XunfeiConfig
from llm_failover import LLMFailoverManager

# 创建主LLM
primary = XunfeiGateway(config)

# 创建备用LLM
fallback = QwenGateway(qwen_config)

# 创建故障转移管理器
failover = LLMFailoverManager(primary, fallback)

# 使用
response = await failover.chat("Hello!")
```
