# Command Confirmation Mechanism

**Author**: YuKaiXu  
**Email**: yukaixu@outlook.com

---

## Overview

When user input is ambiguous or incorrect, prompt for confirmation before execution. This is a hardcoded rule that cannot be modified by LLM.

## Hardcoded Rules

```python
HARDCODED_CONFIRMATION_RULES = {
    "REQUIRE_CONFIRMATION": True,
    "CONFIRMATION_TIMEOUT": 60,
    "MAX_PENDING_CONFIRMATIONS": 10,
    "MODIFIABLE": False
}
```

## Trigger Conditions

| Condition | Description |
|-----------|-------------|
| Ambiguous command | User input doesn't use hardcoded prefix but matches natural language pattern |
| Dangerous command | Shell command marked as dangerous (e.g., rm, chmod, etc.) |
| Incorrect input | User input format is incorrect |

## Confirmation Flow

```
User Input → Pattern Match → Detect Ambiguous Command
                               ↓
                         Generate Suggested Command
                               ↓
                         Send Confirmation Request
                               ↓
                  User Confirm/Cancel → Execute/Abort
```

## Natural Language Matching Patterns

| Natural Language | Translation |
|-----------------|-------------|
| "switch to xxx chatroom" | `g: xxx` |
| "go to xxx room" | `g: xxx` |
| "enter xxx channel" | `g: xxx` |
| "private message xxx saying yyy" | `s: xxx yyy` |
| "send xxx to yyy" | `s: xxx yyy` |
| "send xxx to com" | `com: xxx` |
| "say xxx in com" | `com: xxx` |
| "execute xxx command" | `sh: xxx` |

## Confirmation Request Example

```
⚠️ Command Confirmation Request

Your input: "switch to anonradio chatroom"
Detected as: Room switch
Suggested command: `g: anonradio`

━━━━━━━━━━━━━━━━━━━━━━
Reply "confirm conf_abc123" to confirm
Reply "reject conf_abc123" to cancel
Reply "cancel" to cancel all pending
━━━━━━━━━━━━━━━━━━━━━━
```

## Dangerous Commands List

| Command | Risk Level |
|---------|------------|
| rm | High |
| chmod | High |
| chown | High |
| kill | High |
| dd | High |
| mkfs | High |

## Technical Implementation

```python
class CommandConfirmation:
    def analyze_input(self, user_input: str) -> Optional[PendingConfirmation]:
        if self._has_explicit_prefix(user_input):
            return None
        
        for cmd_type, config in self.FUZZY_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, user_input):
                    return self._create_confirmation(...)
        
        return None
```

## Modification Prohibited

This rule is a core system design that no module (including LLM) may modify or bypass.

---

[中文版本](command_confirmation.md)
