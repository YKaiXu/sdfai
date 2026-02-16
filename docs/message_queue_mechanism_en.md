# Message Queue Mechanism Specification

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

SDFAI adopts a unified message queue mechanism to ensure all messages flow through LLM processing, enabling intelligent routing and security control.

## Hardcoded Rules

The following three rules are core system designs that cannot be modified by LLM or any module:

### Rule 1: Unified Inbound Message Routing

**All messages from SDF, Skills, or other sources must be transmitted to SDFAI core through the message queue.**

```
SDF/Skill → Message Queue → SDFAI → LLM Processing → Routing Decision
```

- Inbound messages uniformly enter the message queue
- SDFAI retrieves messages from the queue
- LLM processes and decides routing direction
- Ensures all messages undergo security checks

### Rule 2: Unified Outbound Message Processing

**All messages sent outward through information channels (including Feishu, etc.) must be processed by SDFAI LLM and transmitted through the message queue.**

```
SDFAI → LLM Processing → Message Queue → SDF/Skill/IM
```

- Outbound messages must be processed by LLM
- Processed messages enter the message queue
- Queue distributes to target channels
- Ensures output content is safe and compliant

### Rule 3: Skills Do Not Manage Queues

**All Skill modules do not need to manage message queues, only need to implement standard interfaces.**

```
Skill ← Standard Interface → SDFAI Core
```

- Skills only handle business logic
- Message queues are managed by SDFAI core
- Skills send/receive messages through standard interfaces
- Reduces Skill development complexity

### Rule 4: Execution Result Reporting

**All special commands must report execution results to the source IM after execution.**

```
Command Execution → Generate Report → Message Queue → Source IM
```

- After COM message sent, report delivery status
- Include NCurses parsed message timestamp as delivery time
- After Shell command executed, report execution result
- After room switched, report switch result
- After private message sent, report send status

### Rule 5: Command Confirmation Mechanism

**When user input is ambiguous or incorrect, prompt for confirmation before execution.**

```
Ambiguous Input → Pattern Match → Generate Suggestion → User Confirm → Execute
```

- Extended command translator matching patterns
- Support natural language expressions (e.g., "switch to xxx chatroom")
- Generate suggested command when ambiguous input detected
- Execute only after user confirmation
- Dangerous commands require confirmation

## Business Routing Logic

### COM Message Routing Flow

```
┌─────────────┐
│  SDF COM    │  User sends message
│  Chat UI    │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ NCurses     │  Parse terminal output, extract message
│ Parser      │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Message     │  Inbound message queue
│ Queue       │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ SDFAI Core  │  Message processing center
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ LLM         │  Intelligent processing, routing decision
│ Processing  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Message     │  Outbound message queue
│ Queue       │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Target IM   │  Feishu/DingTalk/Other IM
│ Send        │
└─────────────┘
```

### Complete Message Flow Architecture

```
┌─────────────┐
│   SDF COM   │
├─────────────┤
│   Feishu    │  ──→  ┌──────────┐  ──→  ┌─────────┐
│   DingTalk  │       │ Message  │       │ SDFAI   │
│   Other IM  │       │ Queue    │       │ Core    │
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
              │ Message  │              │ Message  │              │ Message  │
              │ Queue    │              │ Queue    │              │ Queue    │
              └──────────┘              └──────────┘              └──────────┘
                   ↓                          ↓                          ↓
              ┌──────────┐              ┌──────────┐              ┌──────────┐
              │   SDF    │              │ Feishu   │              │  Skill   │
              └──────────┘              └──────────┘              └──────────┘
```

## Technical Implementation

### Message Queue Interface

```python
class QueueMessage:
    message_id: str
    source: str           # Source: sdf, feishu, skill
    target: str           # Target: sdf, feishu, skill
    content: str
    priority: int         # Priority: 1-10
    timestamp: datetime
    metadata: dict
```

### COM Message Processing Flow

```python
# COM message inbound processing
async def handle_com_message(raw_output: str):
    # 1. NCurses parsing
    parser = NCursesParser()
    screen = parser.parse(raw_output)
    message = extract_chat_message(screen)
    
    # 2. Enter message queue
    queue_msg = QueueMessage(
        source="sdf_com",
        target="sdfai",
        content=message
    )
    await message_queue.enqueue(queue_msg)
    
    # 3. SDFAI processing
    msg = await message_queue.dequeue()
    response = await sdfai.process(msg)
    
    # 4. LLM routing decision
    target = await llm.decide_route(response)
    
    # 5. Send to target IM
    await send_to_im(target, response)
```

### Inbound Flow

```python
# Rule 1 implementation
async def handle_incoming(message: QueueMessage):
    await message_queue.enqueue(message)
    msg = await message_queue.dequeue()
    response = await sdfai.process(msg)
    await route_message(response)
```

### Outbound Flow

```python
# Rule 2 implementation
async def handle_outgoing(message: QueueMessage):
    processed = await llm.process(message)
    await message_queue.enqueue(processed)
    await dispatch_to_target(processed)
```

### Skill Interface

```python
# Rule 3 implementation
class SkillInterface:
    async def receive(self, message: str) -> None:
        pass
    
    async def send(self, response: str) -> None:
        await sdfai.send_to_queue(response)
```

## Security Guarantees

1. **All messages undergo LLM review**
2. **Sensitive operations require user confirmation**
3. **Message queue persistent storage**
4. **Abnormal messages automatically intercepted**

## Modification Prohibited

The above three rules are core system designs that no module (including LLM) may modify or bypass.

---

[中文版本](message_queue_mechanism.md)
