# 技能开发指南

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

SDFAI技能系统支持两种格式：
1. **SDFAI原生格式** - 推荐使用
2. **OpenClaw/Nanobot格式** - 兼容格式

## SDFAI原生格式

### 文件结构

```
skills/installed/my_skill/
├── SKILL.md          # 主技能文件
├── skill.json        # 机器可读配置
└── handler.py        # 可选：自定义处理器
```

### SKILL.md 格式

```markdown
# 天气查询

## Metadata
- Version: 1.0.0
- Description: 查询天气信息

## Triggers
- `天气`
- `weather`

## Actions

### Action 1
```json
{
    "type": "respond",
    "text": "正在查询天气..."
}
```
```

### Action 类型

| 类型 | 说明 | 示例 |
|-----|------|------|
| respond | 文本回复 | `{"type": "respond", "text": "回复内容"}` |
| execute | 执行命令 | `{"type": "execute", "command": "ls"}` |
| api_call | API调用 | `{"type": "api_call", "endpoint": "url"}` |

## 自定义处理器

```python
# skills/installed/my_skill/handler.py
async def handle(text, trigger, skill, context):
    result = await some_operation(text)
    return f"处理结果: {result}"
```

## 最佳实践

1. **单一职责**: 每个技能只做一件事
2. **明确触发词**: 避免与其他技能冲突
3. **错误处理**: 在处理器中处理异常
4. **版本管理**: 使用语义化版本号

---

[English Version](skill_development_en.md)
