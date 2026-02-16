# 配置说明

**作者**: YuKaiXu  
**邮箱**: yukaixu@outlook.com

---

## 配置文件

主配置文件: `sdfai_config.json`

```json
{
    "channels": {
        "sdfcom": {
            "enabled": true,
            "host": "sdf.org",
            "username": "your_username",
            "password": "your_password",
            "room": "lounge"
        },
        "feishu": {
            "enabled": true,
            "app_id": "cli_xxx",
            "app_secret": "xxx"
        },
        "xunfei": {
            "enabled": true,
            "api_key": "xxx",
            "model": "kimi"
        }
    }
}
```

## 通道配置

### COM聊天通道

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| host | 服务器地址 | sdf.org |
| username | 用户名 | 必填 |
| password | 密码 | 必填 |
| room | 默认房间 | lounge |

### 飞书通道

| 参数 | 说明 |
|-----|------|
| app_id | 应用ID |
| app_secret | 应用密钥 |

### 讯飞通道

| 参数 | 说明 |
|-----|------|
| api_key | API密钥 |
| model | 模型名称 |

## 安全配置

```json
{
    "security": {
        "dangerous_commands": ["rm -rf", "dd if="],
        "require_confirmation": true
    }
}
```

---

[English Version](configuration_en.md)
