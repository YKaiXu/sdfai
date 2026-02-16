# OpenClaw 技能兼容性

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 概述

SDFAI完全兼容OpenClaw/Nanobot格式的技能。安装时自动翻译为SDFAI格式。

## 安装方式

### 方式1: 直接拷贝

```bash
# 将OpenClaw技能文件拷贝到incoming目录
cp my_skill.md skills/incoming/

# SDFAI自动检测并翻译安装
```

### 方式2: 从目录安装

```python
from core import SkillManager
from pathlib import Path

manager = SkillManager(Path("skills"))
installed = manager.install_from_directory(Path("/path/to/openclaw/skills"))
print(f"已安装 {len(installed)} 个技能")
```

## OpenClaw 格式示例

```markdown
# 天气查询

## Description
查询指定城市的天气信息

## Triggers
- 天气
- weather
- 今天天气怎么样

## Actions
- 调用天气API获取数据
- 格式化返回结果
- 发送回复消息
```

## 翻译规则

| OpenClaw字段 | SDFAI字段 | 说明 |
|-------------|----------|------|
| # Name | name | 技能名称 |
| ## Description | description | 描述 |
| ## Triggers | triggers | 触发词 |
| ## Actions | actions | 动作列表 |

## 支持的格式

| 格式 | 检测方式 | 支持状态 |
|-----|---------|---------|
| OpenClaw | `## Triggers` + `## Actions` | ✅ 完全支持 |
| Nanobot | `## Commands` + `## Responses` | ✅ 完全支持 |
| JSON | 文件以`{`开头 | ✅ 完全支持 |
| SDFAI | 标准格式 | ✅ 原生支持 |

## 技能文件监控

系统自动监控 `skills/incoming/` 目录：
1. 检测新技能文件
2. 通过IM通知用户
3. 用户确认后翻译安装

---

[English Version](openclaw_compatibility_en.md)
