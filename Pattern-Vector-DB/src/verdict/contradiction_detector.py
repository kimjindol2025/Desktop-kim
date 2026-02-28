"""
Self-Contradiction Detector

DSL 규칙 충돌 감지 - "정책이 잘못됐다"를 자동 감지
규칙 간 모순, 순환 참조, 불가능한 조건 감지
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Any, Optional
from enum import Enum


class ContradictionType(Enum):
    """모순의 종류"""
    DIRECT_CONFLICT = "direct_conflict"          # 직접 충돌
    CIRCULAR_REFERENCE = "circular_reference"    # 순환 참조
    IMPOSSIBLE_CONDITION = "impossible_condition"  # 불가능한 조건
    MUTUAL_EXCLUSION = "mutual_exclusion"        # 상호 배타적
    DEAD_CODE = "dead_code"                      # 도달 불가능 코드
    TAUTOLOGY = "tautology"                      # 항상 참
    CONTRADICTION = "contradiction"               # 항상 거짓


@dataclass
class RuleConflict:
    """규칙 충돌"""
    conflict_type: ContradictionType
    rule_ids: List[str]
    severity: str  # "fatal", "high", "medium", "low"
    description: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "type": self.conflict_type.value,
            "rules": self.rule_ids,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    conflicts: List[RuleConflict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def add_conflict(self, conflict: RuleConflict) -> None:
        """충돌 추가"""
        self.conflicts.append(conflict)

    def add_warning(self, warning: str) -> None:
        """경고 추가"""
        self.warnings.append(warning)

    def to_dict(self) -> Dict:
        return {
            "valid": self.is_valid,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "warnings": self.warnings,
            "statistics": self.stats,
        }


class ContradictionDetector:
    """모순 감지 엔진"""

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}

    def add_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> None:
        """규칙 추가"""
        self.rules[rule_id] = rule_data

    def validate_all_rules(self) -> ValidationResult:
        """모든 규칙 검증"""
        result = ValidationResult(is_valid=True)

        # 1. 직접 충돌 감지
        direct_conflicts = self._detect_direct_conflicts()
        for conflict in direct_conflicts:
            result.add_conflict(conflict)
            result.is_valid = False

        # 2. 순환 참조 감지
        circular_refs = self._detect_circular_references()
        for conflict in circular_refs:
            result.add_conflict(conflict)
            result.is_valid = False

        # 3. 불가능한 조건 감지
        impossible_conds = self._detect_impossible_conditions()
        for conflict in impossible_conds:
            result.add_conflict(conflict)
            if conflict.severity in ["fatal", "high"]:
                result.is_valid = False

        # 4. 도달 불가능 코드 감지
        dead_code = self._detect_dead_code()
        for conflict in dead_code:
            result.add_warning(conflict.description)

        # 통계
        result.stats = {
            "total_rules": len(self.rules),
            "conflicts": len(result.conflicts),
            "warnings": len(result.warnings),
            "fatal_conflicts": sum(
                1 for c in result.conflicts if c.severity == "fatal"
            ),
        }

        return result

    def _detect_direct_conflicts(self) -> List[RuleConflict]:
        """직접 충돌 감지 - 같은 언어에 대해 상반된 판정"""
        conflicts = []

        rule_ids = list(self.rules.keys())
        for i, rule_id_1 in enumerate(rule_ids):
            for rule_id_2 in rule_ids[i+1:]:
                conflict = self._check_rule_conflict(rule_id_1, rule_id_2)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _check_rule_conflict(
        self,
        rule_id_1: str,
        rule_id_2: str,
    ) -> Optional[RuleConflict]:
        """두 규칙의 충돌 확인"""
        rule1 = self.rules[rule_id_1]
        rule2 = self.rules[rule_id_2]

        # 같은 조건에서 다른 결론?
        condition_1 = self._normalize_condition(rule1.get("condition", {}))
        condition_2 = self._normalize_condition(rule2.get("condition", {}))
        action_1 = rule1.get("action", {})
        action_2 = rule2.get("action", {})

        # 조건이 같거나 부분적으로 겹치는데 결론이 다르면?
        if self._conditions_overlap(condition_1, condition_2):
            verdict_1 = action_1.get("verdict")
            verdict_2 = action_2.get("verdict")

            if verdict_1 and verdict_2 and verdict_1 != verdict_2:
                # 상반된 판정
                return RuleConflict(
                    conflict_type=ContradictionType.DIRECT_CONFLICT,
                    rule_ids=[rule_id_1, rule_id_2],
                    severity="high",
                    description=f"Rules {rule_id_1} and {rule_id_2} "
                               f"have conflicting verdicts: "
                               f"{verdict_1} vs {verdict_2}",
                    suggestion=f"Review conditions: "
                              f"{condition_1} vs {condition_2}",
                )

        return None

    def _detect_circular_references(self) -> List[RuleConflict]:
        """순환 참조 감지"""
        conflicts = []

        for rule_id in self.rules:
            if self._has_circular_reference(rule_id):
                conflicts.append(RuleConflict(
                    conflict_type=ContradictionType.CIRCULAR_REFERENCE,
                    rule_ids=[rule_id],
                    severity="fatal",
                    description=f"Rule {rule_id} has circular reference",
                    suggestion="Check rule dependencies and remove cycles",
                ))

        return conflicts

    def _has_circular_reference(self, rule_id: str, visited: Optional[Set[str]] = None) -> bool:
        """순환 참조 확인"""
        if visited is None:
            visited = set()

        if rule_id in visited:
            return True

        visited.add(rule_id)
        rule = self.rules.get(rule_id)

        if not rule:
            return False

        # 규칙이 참조하는 다른 규칙 찾기
        dependencies = self._extract_dependencies(rule)

        for dep in dependencies:
            if self._has_circular_reference(dep, visited.copy()):
                return True

        return False

    def _extract_dependencies(self, rule: Dict[str, Any]) -> Set[str]:
        """규칙의 의존성 추출"""
        dependencies = set()

        # 조건에서 규칙 참조 찾기
        condition = rule.get("condition", {})
        if isinstance(condition, str):
            # 예: "rule_001 AND rule_002" 형태
            for rule_id in self.rules:
                if rule_id in condition:
                    dependencies.add(rule_id)

        return dependencies

    def _detect_impossible_conditions(self) -> List[RuleConflict]:
        """불가능한 조건 감지"""
        conflicts = []

        for rule_id, rule in self.rules.items():
            condition = rule.get("condition", {})

            # requires_all과 requires_none에 겹치는 항목?
            impossible = self._check_impossible_condition(condition)
            if impossible:
                conflicts.append(RuleConflict(
                    conflict_type=ContradictionType.IMPOSSIBLE_CONDITION,
                    rule_ids=[rule_id],
                    severity="high",
                    description=f"Rule {rule_id} has impossible condition: "
                               f"requires both X and not-X",
                    suggestion="Fix the condition logic",
                ))

        return conflicts

    def _check_impossible_condition(self, condition: Dict[str, Any]) -> bool:
        """조건이 불가능한지 확인"""
        requires_all = set(condition.get("requires_all", []))
        requires_none = set(condition.get("requires_none", []))

        # 교집합이 있으면 불가능
        return bool(requires_all & requires_none)

    def _detect_dead_code(self) -> List[RuleConflict]:
        """도달 불가능 코드 감지 - 항상 False인 조건"""
        dead_code = []

        for rule_id, rule in self.rules.items():
            condition = rule.get("condition", {})

            if self._is_always_false(condition):
                dead_code.append(RuleConflict(
                    conflict_type=ContradictionType.DEAD_CODE,
                    rule_ids=[rule_id],
                    severity="medium",
                    description=f"Rule {rule_id} is unreachable "
                               f"(condition always false)",
                    suggestion="Remove or fix this rule",
                ))

        return dead_code

    def _is_always_false(self, condition: Dict[str, Any]) -> bool:
        """조건이 항상 거짓인지 확인"""
        # 단순 휴리스틱
        requires_all = condition.get("requires_all", [])
        requires_none = condition.get("requires_none", [])

        # 같은 것을 동시에 requires와 not requires 하면?
        for item in requires_all:
            if item in requires_none:
                return True

        return False

    def _normalize_condition(self, condition: Dict[str, Any]) -> str:
        """조건을 정규화된 문자열로"""
        if not condition:
            return ""

        parts = []
        if "requires_all" in condition:
            parts.append(f"all({','.join(condition['requires_all'])})")
        if "requires_any" in condition:
            parts.append(f"any({','.join(condition['requires_any'])})")
        if "requires_none" in condition:
            parts.append(f"none({','.join(condition['requires_none'])})")

        return " AND ".join(parts)

    def _conditions_overlap(self, cond1: str, cond2: str) -> bool:
        """두 조건이 겹치는지 확인"""
        # 단순 문자열 비교 (실제로는 더 복잡한 로직 필요)
        if not cond1 or not cond2:
            return False

        # 같은 항목이 포함되어 있으면 겹친다고 봄
        items1 = set(cond1.split())
        items2 = set(cond2.split())

        return bool(items1 & items2)

    def get_conflict_report(self, result: ValidationResult) -> str:
        """충돌 보고서 생성"""
        lines = [
            "# 🚨 Rule Contradiction Report",
            "",
            f"**Valid**: {'✅ Yes' if result.is_valid else '❌ No'}",
            f"**Total Rules**: {result.stats.get('total_rules', 0)}",
            f"**Conflicts**: {result.stats.get('conflicts', 0)}",
            f"**Fatal Conflicts**: {result.stats.get('fatal_conflicts', 0)}",
            "",
        ]

        if result.conflicts:
            lines.extend([
                "## 🔴 Conflicts",
                "",
            ])

            for i, conflict in enumerate(result.conflicts, 1):
                lines.append(f"{i}. **{conflict.conflict_type.value}** "
                           f"(severity: {conflict.severity})")
                lines.append(f"   Rules: {', '.join(conflict.rule_ids)}")
                lines.append(f"   Issue: {conflict.description}")
                if conflict.suggestion:
                    lines.append(f"   Suggestion: {conflict.suggestion}")
                lines.append("")

        if result.warnings:
            lines.extend([
                "## ⚠️ Warnings",
                "",
            ])

            for warning in result.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def suggest_fixes(self, result: ValidationResult) -> List[str]:
        """수정 제안 생성"""
        suggestions = []

        for conflict in result.conflicts:
            if conflict.suggestion:
                suggestions.append(
                    f"[{', '.join(conflict.rule_ids)}] {conflict.suggestion}"
                )

        return suggestions
