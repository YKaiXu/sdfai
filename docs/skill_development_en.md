# Skill Development Guide

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

SDFAI skill system supports two formats:
1. **SDFAI Native Format** - Recommended
2. **OpenClaw/Nanobot Format** - Compatible

## SDFAI Native Format

### File Structure

```
skills/installed/my_skill/
├── SKILL.md          # Main skill file
├── skill.json        # Machine-readable config
└── handler.py        # Optional: custom handler
```

### SKILL.md Format

```markdown
# Weather Query

## Metadata
- Version: 1.0.0
- Description: Query weather information

## Triggers
- `weather`
- `forecast`

## Actions

### Action 1
```json
{
    "type": "respond",
    "text": "Querying weather..."
}
```
```

### Action Types

| Type | Description | Example |
|------|-------------|---------|
| respond | Text response | `{"type": "respond", "text": "Response"}` |
| execute | Execute command | `{"type": "execute", "command": "ls"}` |
| api_call | API call | `{"type": "api_call", "endpoint": "url"}` |

## Custom Handler

```python
# skills/installed/my_skill/handler.py
async def handle(text, trigger, skill, context):
    result = await some_operation(text)
    return f"Result: {result}"
```

## Best Practices

1. **Single Responsibility**: Each skill does one thing
2. **Clear Triggers**: Avoid conflicts with other skills
3. **Error Handling**: Handle exceptions in handlers
4. **Versioning**: Use semantic versioning

---

[中文版本](skill_development.md)
