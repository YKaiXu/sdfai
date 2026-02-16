"""
Security Evaluator - LLM安全评估器
在安装插件或执行操作前，由LLM进行安全评估
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .security import SecurityManager, SecurityLevel
from .stability import StabilityManager, StabilityStatus


class EvaluationAction(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"
    QUARANTINE = "quarantine"


@dataclass
class EvaluationResult:
    action: EvaluationAction
    confidence: float
    risks: List[str]
    recommendations: List[str]
    details: str
    timestamp: datetime = field(default_factory=datetime.now)


SECURITY_EVALUATION_PROMPT = """
You are a security evaluator for SDFAI system. Analyze the following content for security risks.

Content to evaluate:
{content}

Context:
{context}

Evaluate for:
1. Code injection risks
2. Data exfiltration risks  
3. System modification risks
4. Network security risks
5. Privilege escalation risks

Respond in JSON format:
{{
    "risk_level": "safe|low|medium|high|critical",
    "confidence": 0.0-1.0,
    "risks": ["risk1", "risk2"],
    "recommendations": ["rec1", "rec2"],
    "details": "explanation"
}}
"""


class SecurityEvaluator:
    MIN_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(
        self, 
        data_dir: Path,
        security_manager: SecurityManager,
        stability_manager: StabilityManager,
        llm_client: Callable = None
    ):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.security_manager = security_manager
        self.stability_manager = stability_manager
        self.llm_client = llm_client
        self.evaluation_history: List[Dict] = []
    
    async def evaluate_command(self, command: str, context: Dict = None) -> EvaluationResult:
        static_result = self.security_manager.evaluate_command(command)
        
        if static_result in [SecurityLevel.CRITICAL, SecurityLevel.BLOCKED]:
            return EvaluationResult(
                action=EvaluationAction.DENY,
                confidence=1.0,
                risks=[f"Static analysis detected {static_result.value} risk"],
                recommendations=["This command is not allowed"],
                details=f"Blocked by security rule"
            )
        
        stability_status = self.stability_manager.evaluate_stability()
        if stability_status in [StabilityStatus.CRITICAL, StabilityStatus.EMERGENCY]:
            return EvaluationResult(
                action=EvaluationAction.DENY,
                confidence=1.0,
                risks=[f"System unstable: {stability_status.value}"],
                recommendations=["Wait for system to stabilize"],
                details="Command rejected due to system instability"
            )
        
        if self.llm_client:
            llm_result = await self._llm_evaluate(command, "command_execution", context or {})
            return llm_result
        
        return EvaluationResult(
            action=EvaluationAction.CONFIRM,
            confidence=0.5,
            risks=["LLM evaluation unavailable"],
            recommendations=["Manual review recommended"],
            details="Static analysis only"
        )
    
    async def _llm_evaluate(self, content: str, eval_type: str, context: Dict) -> EvaluationResult:
        try:
            prompt = SECURITY_EVALUATION_PROMPT.format(
                content=content[:2000],
                context=json.dumps(context, ensure_ascii=False)
            )
            
            response = await self.llm_client(prompt)
            result_data = self._parse_llm_response(response)
            
            return self._llm_result_to_evaluation(result_data)
            
        except Exception as e:
            return EvaluationResult(
                action=EvaluationAction.CONFIRM,
                confidence=0.3,
                risks=[f"LLM evaluation error: {str(e)}"],
                recommendations=["Manual review required"],
                details="LLM evaluation failed"
            )
    
    def _parse_llm_response(self, response: str) -> Dict:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return {
            "risk_level": "medium",
            "confidence": 0.5,
            "risks": ["Unable to parse LLM response"],
            "recommendations": ["Manual review recommended"],
            "details": response[:200]
        }
    
    def _llm_result_to_evaluation(self, result: Dict) -> EvaluationResult:
        risk_level = result.get("risk_level", "medium")
        confidence = result.get("confidence", 0.5)
        risks = result.get("risks", [])
        recommendations = result.get("recommendations", [])
        details = result.get("details", "")
        
        if risk_level == "critical":
            action = EvaluationAction.DENY
        elif risk_level == "high":
            action = EvaluationAction.QUARANTINE
        elif risk_level == "medium":
            action = EvaluationAction.CONFIRM
        elif confidence < self.MIN_CONFIDENCE_THRESHOLD:
            action = EvaluationAction.CONFIRM
        else:
            action = EvaluationAction.ALLOW
        
        return EvaluationResult(
            action=action,
            confidence=confidence,
            risks=risks,
            recommendations=recommendations,
            details=details
        )
