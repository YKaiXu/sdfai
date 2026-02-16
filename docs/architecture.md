# 架构设计

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 核心设计哲学

**一切皆文件** - Unix哲学在AI系统中的应用

所有通讯、配置、技能都以文件形式存储：
- 消息存储在 `inbox/` 和 `outbox/` 目录
- 状态存储在 `status.json`
- 技能存储为Markdown和JSON文件

## 目录结构

```
sdfai/
├── channel/           # 通讯通道
├── core/              # AI核心模块
│   └── sec/           # 安全模块
├── sdf/               # SDF.org模块
├── memory/            # 记忆存储
├── skills/            # 技能目录
└── docs/              # 文档
```

## 消息流转

```
用户消息 → Channel.inbox → AI处理 → Channel.outbox → 发送
                ↓
           memory/
```

## 核心组件

| 模块 | 描述 |
|-----|------|
| channel | 通讯通道 (飞书, 讯飞, COM聊天) |
| core | AI引擎, 记忆, 路由, 守护进程 |
| core/sec | 安全, 稳定性, 评估器, 加固 |
| sdf | AsyncSSH连接, 命令翻译 |
| memory | SQLite, 向量, 文件存储 |
| skills | OpenClaw兼容技能系统 |

## 安全设计

1. **硬编码命令前缀**: `com:`, `sh:`, `g:`, `s:`
2. **强制AsyncSSH**: 所有SSH连接使用AsyncSSH
3. **LLM安全评估**: 所有操作经过LLM评估
4. **用户确认**: 敏感操作需用户确认

## 通用性设计

SDFAI不仅限于SDF.org，可用于：
- 任何Linux服务器管理
- 多种IM平台集成
- AI辅助运维
- 安全监控与加固

---

[English Version](architecture_en.md)
