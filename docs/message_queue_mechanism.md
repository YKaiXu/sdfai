# 消息队列机制说明

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

SDFAI采用统一的消息队列机制，确保所有消息流转经过LLM处理，实现智能路由和安全控制。

## 硬编码规则

以下三条规则为系统核心设计，不可被LLM或任何模块修改：

### 规则一：入站消息统一路由

**所有来自SDF、Skill或其他来源的消息，必须经过消息队列传输给SDFAI核心。**

```
SDF/Skill → 消息队列 → SDFAI → LLM处理 → 路由决策
```

- 入站消息统一进入消息队列
- SDFAI从队列获取消息
- LLM处理后决定路由方向
- 确保所有消息经过安全检查

### 规则二：出站消息统一处理

**所有信息通道（包括飞书等）向外发送的消息，必须经过SDFAI LLM处理后，经由消息队列传送。**

```
SDFAI → LLM处理 → 消息队列 → SDF/Skill/IM
```

- 出站消息必须经过LLM处理
- 处理后进入消息队列
- 由队列分发到目标通道
- 确保输出内容安全合规

### 规则三：Skill无需管理队列

**所有Skill模块无需管理消息队列，只需实现标准接口。**

```
Skill ← 标准接口 → SDFAI核心
```

- Skill只负责业务逻辑
- 消息队列由SDFAI核心管理
- Skill通过标准接口收发消息
- 降低Skill开发复杂度

### 规则四：执行结果报告

**所有特殊指令执行后，必须向指令发出的IM报告执行结果。**

```
指令执行 → 生成报告 → 消息队列 → 源IM
```

- COM消息发送后，报告送达状态
- 附带NCurses解析出的消息时间戳作为送达时间
- Shell命令执行后，报告执行结果
- 房间切换后，报告切换结果
- 私聊发送后，报告发送状态

### 规则五：命令确认机制

**用户输入错误或模糊指令时，提示用户确认后再执行。**

```
模糊输入 → 模式匹配 → 生成建议 → 用户确认 → 执行
```

- 扩展命令翻译器匹配模式
- 支持自然语言表达（如"切换到xxx聊天室"）
- 检测到模糊指令时，生成建议命令
- 用户确认后才执行
- 危险命令必须确认

## 业务路由逻辑

### COM消息路由流程

```
┌─────────────┐
│  SDF COM    │  用户发送消息
│  聊天界面   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ NCurses解析 │  解析终端输出，提取消息内容
│  提取消息   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  消息队列   │  入站消息队列
│  (入站)     │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  SDFAI核心  │  消息处理中心
└──────┬──────┘
       │
       ↓
┌─────────────┐
│    LLM      │  智能处理，路由决策
│  处理决策   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  消息队列   │  出站消息队列
│  (出站)     │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  对应IM     │  飞书/钉钉/其他IM
│  发送消息   │
└─────────────┘
```

### 完整消息流转架构

```
┌─────────────┐
│   SDF COM   │
├─────────────┤
│   飞书 IM    │  ──→  ┌──────────┐  ──→  ┌─────────┐
│   钉钉 IM    │       │ 消息队列  │       │ SDFAI   │
│   其他 IM    │       └──────────┘       │  核心   │
├─────────────┤            ↑              └─────────┘
│   Skills    │ ──────────┘                    │
└─────────────┘                                ↓
                                          ┌─────────┐
                                          │   LLM   │
                                          └─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ↓                          ↓                          ↓
              ┌──────────┐              ┌──────────┐              ┌──────────┐
              │ 消息队列  │              │ 消息队列  │              │ 消息队列  │
              └──────────┘              └──────────┘              └──────────┘
                   ↓                          ↓                          ↓
              ┌──────────┐              ┌──────────┐              ┌──────────┐
              │   SDF    │              │  飞书    │              │  Skill   │
              └──────────┘              └──────────┘              └──────────┘
```

## 技术实现

### 消息队列接口

```python
class QueueMessage:
    message_id: str
    source: str           # 来源：sdf, feishu, skill
    target: str           # 目标：sdf, feishu, skill
    content: str
    priority: int         # 优先级：1-10
    timestamp: datetime
    metadata: dict
```

### COM消息处理流程

```python
# COM消息入站处理
async def handle_com_message(raw_output: str):
    # 1. NCurses解析
    parser = NCursesParser()
    screen = parser.parse(raw_output)
    message = extract_chat_message(screen)
    
    # 2. 进入消息队列
    queue_msg = QueueMessage(
        source="sdf_com",
        target="sdfai",
        content=message
    )
    await message_queue.enqueue(queue_msg)
    
    # 3. SDFAI处理
    msg = await message_queue.dequeue()
    response = await sdfai.process(msg)
    
    # 4. LLM路由决策
    target = await llm.decide_route(response)
    
    # 5. 发送到目标IM
    await send_to_im(target, response)
```

### 入站流程

```python
# 规则一实现
async def handle_incoming(message: QueueMessage):
    await message_queue.enqueue(message)
    msg = await message_queue.dequeue()
    response = await sdfai.process(msg)
    await route_message(response)
```

### 出站流程

```python
# 规则二实现
async def handle_outgoing(message: QueueMessage):
    processed = await llm.process(message)
    await message_queue.enqueue(processed)
    await dispatch_to_target(processed)
```

### Skill接口

```python
# 规则三实现
class SkillInterface:
    async def receive(self, message: str) -> None:
        pass
    
    async def send(self, response: str) -> None:
        await sdfai.send_to_queue(response)
```

## 安全保障

1. **所有消息经过LLM审查**
2. **敏感操作需要用户确认**
3. **消息队列持久化存储**
4. **异常消息自动拦截**

## 禁止修改

以上三条规则为系统核心设计，任何模块（包括LLM）不得修改或绕过。

---

[English Version](message_queue_mechanism_en.md)
