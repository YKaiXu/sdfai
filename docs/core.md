# Core 核心模块

## 概述

Core模块是SDFAI的核心功能模块，包含消息队列、记忆管理、路由、守护进程等核心组件。

## 子模块

### message_queue.py - 消息队列
- **功能**: 异步消息处理，优先级队列
- **类**: QueueManager, MessageQueue, QueueMessage
- **用途**: 管理消息的入队、出队、优先级处理

### memory.py - 记忆管理
- **功能**: 对话记忆存储和检索
- **类**: MemoryManager, Memory
- **用途**: 存储用户对话历史，支持上下文记忆

### router.py - 消息路由
- **功能**: 消息路由和分发
- **类**: MessageRouter, RouteType
- **用途**: 根据消息类型路由到不同处理器

### daemon.py - 守护进程
- **功能**: 系统守护进程管理
- **类**: CoreDaemon, DaemonStatus
- **用途**: 监控系统状态，自动恢复

### thread_manager.py - 线程管理
- **功能**: 异步任务管理
- **类**: ThreadManager, TaskInfo
- **用途**: 管理后台任务和定时任务

### ai_engine.py - AI引擎
- **功能**: AI处理核心
- **类**: AIEngine, AIContext
- **用途**: 统一AI处理接口

## 安全模块 (sec/)

### security.py - 安全管理
- 输入验证、权限检查

### stability.py - 稳定性管理
- 系统稳定性监控

### evaluator.py - 安全评估
- 安全风险评估

### hardening.py - 安全加固
- 系统安全加固措施
