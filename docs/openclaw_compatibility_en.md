# OpenClaw Skill Compatibility

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

SDFAI is fully compatible with OpenClaw/Nanobot format skills. Skills are automatically translated to SDFAI format during installation.

## Installation Methods

### Method 1: Direct Copy

```bash
# Copy OpenClaw skill file to incoming directory
cp my_skill.md skills/incoming/

# SDFAI automatically detects and translates
```

### Method 2: Install from Directory

```python
from core import SkillManager
from pathlib import Path

manager = SkillManager(Path("skills"))
installed = manager.install_from_directory(Path("/path/to/openclaw/skills"))
print(f"Installed {len(installed)} skills")
```

## OpenClaw Format Example

```markdown
# Weather Query

## Description
Query weather information for specified city

## Triggers
- weather
- forecast
- what's the weather

## Actions
- Call weather API to get data
- Format the result
- Send response message
```

## Translation Rules

| OpenClaw Field | SDFAI Field | Description |
|----------------|-------------|-------------|
| # Name | name | Skill name |
| ## Description | description | Description |
| ## Triggers | triggers | Trigger words |
| ## Actions | actions | Action list |

## Supported Formats

| Format | Detection Method | Support Status |
|--------|------------------|----------------|
| OpenClaw | `## Triggers` + `## Actions` | ✅ Fully Supported |
| Nanobot | `## Commands` + `## Responses` | ✅ Fully Supported |
| JSON | File starts with `{` | ✅ Fully Supported |
| SDFAI | Standard format | ✅ Native Support |

## Skill File Monitoring

System automatically monitors `skills/incoming/` directory:
1. Detect new skill files
2. Notify user via IM
3. Translate and install after user confirmation

---

[中文版本](openclaw_compatibility.md)
