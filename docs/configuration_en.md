# Configuration Guide

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Configuration File

Main configuration file: `sdfai_config.json`

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

## Channel Configuration

### COM Chat Channel

| Parameter | Description | Default |
|-----------|-------------|---------|
| host | Server address | sdf.org |
| username | Username | Required |
| password | Password | Required |
| room | Default room | lounge |

### Feishu Channel

| Parameter | Description |
|-----------|-------------|
| app_id | Application ID |
| app_secret | Application secret |

### Xunfei Channel

| Parameter | Description |
|-----------|-------------|
| api_key | API key |
| model | Model name |

## Security Configuration

```json
{
    "security": {
        "dangerous_commands": ["rm -rf", "dd if="],
        "require_confirmation": true
    }
}
```

---

[中文版本](configuration.md)
