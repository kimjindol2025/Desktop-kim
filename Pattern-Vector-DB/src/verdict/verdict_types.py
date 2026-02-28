"""
Type definitions for Verdict Engine
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


class VerdictLevel(Enum):
    """Verdict judgment levels"""
    OPTIMAL = "optimal"      # 최적 선택
    SAFE = "safe"            # 안전
    CAUTION = "caution"      # 주의 필요
    FORBIDDEN = "forbidden"  # 절대 불가


class SeverityLevel(Enum):
    """Constraint severity levels"""
    FATAL = "fatal"        # 즉시 탈락
    HIGH = "high"          # 높음
    MEDIUM = "medium"      # 중간
    LOW = "low"            # 낮음


class CapabilityStrength(Enum):
    """Capability strength levels"""
    CRITICAL = "critical"  # 필수
    HIGH = "high"          # 높음
    MEDIUM = "medium"      # 중간
    LOW = "low"            # 낮음


@dataclass
class Constraint:
    """Language constraint that can forbid a language"""
    key: str
    value: str
    severity: SeverityLevel
    weight: float = 1.0
    reason: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    source: str = "storage"
    confidence: float = 0.95

    def matches(self, requirements: Dict[str, Any]) -> bool:
        """Check if this constraint applies to given requirements"""
        req_value = requirements.get(self.key)
        if req_value is None:
            return False

        # Exact match or list membership
        if isinstance(req_value, list):
            return self.value in req_value
        return req_value == self.value

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "value": self.value,
            "severity": self.severity.value,
            "weight": self.weight,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class Capability:
    """Language capability (positive assertion)"""
    name: str
    strength: str = "medium"  # Accept string for flexibility with JSONL data
    weight: float = 1.0
    source: str = "storage"
    confidence: float = 0.95

    def score_value(self) -> int:
        """Get score adjustment value for this capability"""
        strength_map = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1,
        }
        # Handle both string and enum values
        strength_str = self.strength if isinstance(self.strength, str) else self.strength.value
        return strength_map.get(strength_str, 2)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "strength": self.strength.value,
            "weight": self.weight,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class Verdict:
    """Individual language verdict"""
    language: str
    level: VerdictLevel
    score: int
    reasoning: str
    constraints_checked: int = 0
    constraints_passed: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "language": self.language,
            "verdict": self.level.value,
            "score": self.score,
            "reasoning": self.reasoning,
            "constraints_checked": self.constraints_checked,
            "constraints_passed": self.constraints_passed,
        }


@dataclass
class RejectedLanguage:
    """Rejected language with reason"""
    language: str
    reason: str
    fatal_constraint: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "language": self.language,
            "reason": self.reason,
            "fatal_constraint": self.fatal_constraint,
        }


@dataclass
class LanguageVerdict:
    """Complete verdict for a language"""
    language: str
    verdict: VerdictLevel
    score: int
    reasoning: str
    constraints_checked: int
    constraints_passed: int
    matching_constraints: List[str] = field(default_factory=list)
    matching_capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "language": self.language,
            "verdict": self.verdict.value,
            "score": self.score,
            "reasoning": self.reasoning,
            "constraints_checked": self.constraints_checked,
            "constraints_passed": self.constraints_passed,
            "matching_constraints": self.matching_constraints,
            "matching_capabilities": self.matching_capabilities,
        }


@dataclass
class VerdictSummary:
    """Summary statistics for verdicts"""
    total_evaluated: int
    rejected: int
    caution: int
    safe: int
    optimal: int

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_evaluated": self.total_evaluated,
            "rejected": self.rejected,
            "caution": self.caution,
            "safe": self.safe,
            "optimal": self.optimal,
        }


@dataclass
class VerdictDSLRule:
    """Parsed Verdict DSL rule"""
    rule_id: str
    condition: Dict[str, Any]  # when clause
    action: Dict[str, Any]     # then clause
    reason: str
    confidence: float
    applies_to: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "condition": self.condition,
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "applies_to": self.applies_to,
        }


@dataclass
class FinalVerdict:
    """Final verdict output"""
    request_id: str
    timestamp: str
    requirement: Dict[str, Any]
    verdicts: List[LanguageVerdict]
    rejected_languages: List[RejectedLanguage]
    summary: VerdictSummary
    engine_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "requirement": self.requirement,
            "verdict": {
                "languages": [v.to_dict() for v in self.verdicts],
                "rejected_languages": [r.to_dict() for r in self.rejected_languages],
                "summary": self.summary.to_dict(),
            },
            "engine_info": self.engine_info,
        }
