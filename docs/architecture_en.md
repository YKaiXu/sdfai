# Architecture Design

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Core Design Philosophy

**Everything is a File** - Unix philosophy applied to AI systems

All communications, configurations, and skills are stored as files:
- Messages stored in `inbox/` and `outbox/` directories
- Status stored in `status.json`
- Skills stored as Markdown and JSON files

## Directory Structure

```
sdfai/
├── channel/           # Communication channels
├── core/              # AI core modules
│   └── sec/           # Security modules
├── sdf/               # SDF.org modules
├── memory/            # Memory storage
├── skills/            # Skills directory
└── docs/              # Documentation
```

## Message Flow

```
User Message → Channel.inbox → AI Processing → Channel.outbox → Send
                   ↓
              memory/
```

## Core Components

| Module | Description |
|--------|-------------|
| channel | Communication channels (Feishu, Xunfei, COM chat) |
| core | AI engine, memory, router, daemon |
| core/sec | Security, stability, evaluator, hardening |
| sdf | AsyncSSH connection, command translator |
| memory | SQLite, Vector, File storage |
| skills | OpenClaw compatible skill system |

## Security Design

1. **Hardcoded Command Prefixes**: `com:`, `sh:`, `g:`, `s:`
2. **AsyncSSH Required**: All SSH connections use AsyncSSH
3. **LLM Security Evaluation**: All operations evaluated by LLM
4. **User Confirmation**: Sensitive operations require confirmation

## Universal Design

SDFAI is not limited to SDF.org, it can be used for:
- Any Linux server management
- Multiple IM platform integration
- AI-assisted operations
- Security monitoring and hardening

---

[中文版本](architecture.md)
