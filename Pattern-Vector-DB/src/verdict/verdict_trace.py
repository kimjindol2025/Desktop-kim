"""
Verdict Trace System

판정 이유 추적 - 완전한 결정 체인 기록
constraint → rule → score 전체 파이프라인 추적
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


@dataclass
class TraceStep:
    """추적 단계 - 판정 과정의 한 단계"""
    step_id: str
    step_type: str  # "requirement_normalize", "constraint_check", "capability_score", etc.
    timestamp: str
    language: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str
    confidence: float = 1.0
    duration_ms: int = 0

    def to_dict(self) -> Dict:
        """Dictionary로 변환"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "timestamp": self.timestamp,
            "language": self.language,
            "input": self.input_data,
            "output": self.output_data,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ConstraintCheckTrace:
    """제약 검사 추적"""
    constraint_key: str
    constraint_value: str
    severity: str
    matched: bool
    reason: str
    score_impact: int

    def to_dict(self) -> Dict:
        return {
            "constraint": f"{self.constraint_key}={self.constraint_value}",
            "severity": self.severity,
            "matched": self.matched,
            "reason": self.reason,
            "score_impact": self.score_impact,
        }


@dataclass
class RuleApplicationTrace:
    """규칙 적용 추적"""
    rule_id: str
    rule_type: str  # "dsl", "builtin", "custom"
    condition_matched: bool
    action_taken: str
    score_adjustment: int
    reasoning: str

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "condition_matched": self.condition_matched,
            "action": self.action_taken,
            "score_adjustment": self.score_adjustment,
            "reasoning": self.reasoning,
        }


@dataclass
class VerdictTraceChain:
    """완전한 판정 추적 체인"""
    verdict_id: str
    language: str
    created_at: str

    # 추적 단계
    steps: List[TraceStep] = field(default_factory=list)

    # 상세 추적
    requirement_normalization: Optional[Dict] = None
    constraint_checks: List[ConstraintCheckTrace] = field(default_factory=list)
    rule_applications: List[RuleApplicationTrace] = field(default_factory=list)

    # 최종 결과
    initial_score: int = 100
    final_score: int = 100
    score_adjustments: List[Dict] = field(default_factory=list)
    final_verdict: str = "safe"

    # 통계
    total_constraints_checked: int = 0
    total_constraints_matched: int = 0
    total_rules_applied: int = 0
    total_duration_ms: int = 0

    def add_step(self, step: TraceStep) -> None:
        """추적 단계 추가"""
        self.steps.append(step)

    def add_constraint_check(self, check: ConstraintCheckTrace) -> None:
        """제약 검사 추가"""
        self.constraint_checks.append(check)
        self.total_constraints_checked += 1
        if check.matched:
            self.total_constraints_matched += 1

    def add_rule_application(self, rule: RuleApplicationTrace) -> None:
        """규칙 적용 추가"""
        self.rule_applications.append(rule)
        if rule.condition_matched:
            self.total_rules_applied += 1
            # 점수 조정 기록
            self.score_adjustments.append({
                "rule": rule.rule_id,
                "adjustment": rule.score_adjustment,
                "reasoning": rule.reasoning,
            })

    def get_constraint_chain(self) -> List[Dict]:
        """제약 검사 체인 반환"""
        return [c.to_dict() for c in self.constraint_checks]

    def get_rule_chain(self) -> List[Dict]:
        """규칙 적용 체인 반환"""
        return [r.to_dict() for r in self.rule_applications]

    def get_score_chain(self) -> List[Dict]:
        """점수 조정 체인 반환"""
        chain = [{"stage": "initial", "score": self.initial_score}]
        current_score = self.initial_score

        for adjustment in self.score_adjustments:
            current_score += adjustment["adjustment"]
            chain.append({
                "stage": adjustment["rule"],
                "adjustment": adjustment["adjustment"],
                "score": current_score,
                "reasoning": adjustment["reasoning"],
            })

        return chain

    def to_dict(self) -> Dict:
        """완전한 추적 정보를 Dictionary로 반환"""
        return {
            "verdict_id": self.verdict_id,
            "language": self.language,
            "created_at": self.created_at,
            "trace": {
                "steps": [s.to_dict() for s in self.steps],
                "requirement_normalization": self.requirement_normalization,
                "constraint_checks": self.get_constraint_chain(),
                "rule_applications": self.get_rule_chain(),
                "score_chain": self.get_score_chain(),
            },
            "statistics": {
                "initial_score": self.initial_score,
                "final_score": self.final_score,
                "constraints_checked": self.total_constraints_checked,
                "constraints_matched": self.total_constraints_matched,
                "rules_applied": self.total_rules_applied,
                "total_duration_ms": self.total_duration_ms,
            },
            "final_verdict": self.final_verdict,
        }

    def to_json(self) -> str:
        """JSON으로 직렬화"""
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown_report(self) -> str:
        """인간이 읽을 수 있는 마크다운 보고서"""
        report_lines = [
            "# 🔍 Verdict Trace Report",
            "",
            f"**Language**: {self.language}",
            f"**Verdict**: {self.final_verdict}",
            f"**Score**: {self.initial_score} → {self.final_score}",
            f"**Created**: {self.created_at}",
            "",
            "## 📋 Requirement Normalization",
            "",
        ]

        if self.requirement_normalization:
            for key, value in self.requirement_normalization.items():
                report_lines.append(f"- {key}: {value}")
        report_lines.append("")

        report_lines.extend([
            "## ⚙️ Constraint Checks",
            "",
            f"Total: {self.total_constraints_checked} checked, "
            f"{self.total_constraints_matched} matched",
            "",
        ])

        for i, check in enumerate(self.constraint_checks, 1):
            status = "❌" if check.matched else "✅"
            report_lines.append(
                f"{i}. {status} {check.constraint_key}={check.constraint_value} "
                f"(severity: {check.severity})"
            )
            report_lines.append(f"   Reason: {check.reason}")
            if check.score_impact != 0:
                report_lines.append(f"   Impact: {check.score_impact:+d} points")
            report_lines.append("")

        report_lines.extend([
            "## 🎯 Rule Applications",
            "",
            f"Total: {self.total_rules_applied} rules applied",
            "",
        ])

        for i, rule in enumerate(self.rule_applications, 1):
            if rule.condition_matched:
                report_lines.append(
                    f"{i}. ✅ Rule {rule.rule_id} ({rule.rule_type})"
                )
                report_lines.append(f"   Action: {rule.action_taken}")
                report_lines.append(f"   Adjustment: {rule.score_adjustment:+d} points")
                report_lines.append(f"   Reasoning: {rule.reasoning}")
                report_lines.append("")

        report_lines.extend([
            "## 📊 Score Chain",
            "",
        ])

        score_chain = self.get_score_chain()
        for stage in score_chain:
            if "adjustment" in stage:
                report_lines.append(
                    f"- {stage['stage']}: {stage['score']} "
                    f"({stage['adjustment']:+d}) - {stage['reasoning']}"
                )
            else:
                report_lines.append(f"- Initial: {stage['score']}")

        report_lines.extend([
            "",
            "## 📈 Statistics",
            "",
            f"- Total Duration: {self.total_duration_ms}ms",
            f"- Constraints Checked: {self.total_constraints_checked}",
            f"- Constraints Matched: {self.total_constraints_matched}",
            f"- Rules Applied: {self.total_rules_applied}",
            f"- Final Score: {self.final_score}/100",
        ])

        return "\n".join(report_lines)


class VerdictTracer:
    """판정 추적 시스템"""

    def __init__(self):
        self.traces: Dict[str, VerdictTraceChain] = {}

    def create_trace(self, verdict_id: str, language: str) -> VerdictTraceChain:
        """새로운 추적 생성"""
        trace = VerdictTraceChain(
            verdict_id=verdict_id,
            language=language,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.traces[verdict_id] = trace
        return trace

    def get_trace(self, verdict_id: str) -> Optional[VerdictTraceChain]:
        """추적 조회"""
        return self.traces.get(verdict_id)

    def save_trace(self, verdict_id: str, file_path: str) -> None:
        """추적을 파일에 저장"""
        trace = self.traces.get(verdict_id)
        if not trace:
            raise ValueError(f"Trace not found: {verdict_id}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(trace.to_json())

    def load_trace(self, file_path: str) -> VerdictTraceChain:
        """파일에서 추적 로드"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        trace = VerdictTraceChain(
            verdict_id=data["verdict_id"],
            language=data["language"],
            created_at=data["created_at"],
            initial_score=data["statistics"]["initial_score"],
            final_score=data["statistics"]["final_score"],
            final_verdict=data["final_verdict"],
            total_constraints_checked=data["statistics"]["constraints_checked"],
            total_constraints_matched=data["statistics"]["constraints_matched"],
            total_rules_applied=data["statistics"]["rules_applied"],
            total_duration_ms=data["statistics"]["total_duration_ms"],
        )

        return trace

    def generate_report(self, verdict_id: str) -> str:
        """보고서 생성"""
        trace = self.traces.get(verdict_id)
        if not trace:
            raise ValueError(f"Trace not found: {verdict_id}")

        return trace.to_markdown_report()
