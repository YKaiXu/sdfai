# Memory 记忆模块

## 概述

Memory模块提供多种记忆存储方式，支持SQLite、文件、向量存储。

## 存储类型

### sqlite.py - SQLite存储
- **功能**: SQLite数据库存储
- **类**: SQLiteMemory
- **用途**: 持久化对话记忆
- **特点**: 支持查询、索引

### file.py - 文件存储
- **功能**: 文件系统存储
- **类**: FileMemory
- **用途**: 简单文件存储
- **特点**: 易于备份和迁移

### vector.py - 向量存储
- **功能**: 向量语义存储
- **类**: VectorMemory
- **用途**: 语义搜索
- **特点**: 支持相似度检索

### base.py - 基础接口
- **功能**: 记忆存储基类
- **类**: BaseMemory
- **用途**: 统一存储接口

## 使用示例

```python
from memory import SQLiteMemory

# 创建存储
memory = SQLiteMemory("/path/to/db.sqlite")

# 存储记忆
await memory.store("key", "content", metadata={"type": "chat"})

# 检索记忆
result = await memory.retrieve("key")

# 搜索相似内容
results = await memory.search("query", limit=10)
```
