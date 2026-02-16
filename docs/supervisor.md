# Supervisor AI幻觉监督模块

## 概述

Supervisor模块使用Qwen模型监督主LLM输出，防止AI幻觉问题。

## 功能

### AI幻觉检测
- 检查AI是否声称执行了未实际执行的操作
- 验证AI输出是否与实际结果矛盾
- 检测AI是否编造不存在的信息

### 异步监督
- 不阻塞主流程
- 后台异步执行
- 结果记录到日志

### 故障转移
- 主LLM失败时自动切换
- Qwen作为备用LLM

## 架构

```
用户消息 ──▶ Kimi处理 ──▶ 直接返回用户
                │
                └──▶ Qwen异步监督（不阻塞）
                       │
                       ├─ 正常：记录日志
                       └─ 异常：发送警告
```

## 使用示例

```python
from supervisor import AIHallucinationSupervisor

# 创建监督器
supervisor = AIHallucinationSupervisor()
await supervisor.initialize()

# 异步监督（不阻塞）
await supervisor.supervise_async(
    operation="switch_room",
    input_data="g:hackers",
    ai_output="已切换到房间hackers",
    actual_result="成功"  # 可选
)
```

## 监督记录

每次监督都会记录：
- 操作类型
- 用户输入
- AI输出
- 实际结果
- 是否有效
- 问题列表
- 置信度
