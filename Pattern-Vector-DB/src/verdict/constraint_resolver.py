"""
Constraint Resolution Engine

Resolves conflicting constraints using priority-based approach
"""

from typing import Dict, List, Tuple, Any, Optional
from .verdict_types import Constraint, SeverityLevel, VerdictLevel


class ConstraintResolver:
    """Resolves multiple constraints with priority ranking"""

    SEVERITY_RANK = {
        SeverityLevel.FATAL: 4,
        SeverityLevel.HIGH: 3,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 1,
    }

    SEVERITY_TO_VERDICT = {
        SeverityLevel.FATAL: VerdictLevel.FORBIDDEN,
        SeverityLevel.HIGH: VerdictLevel.CAUTION,
        SeverityLevel.MEDIUM: VerdictLevel.CAUTION,
        SeverityLevel.LOW: VerdictLevel.SAFE,
    }

    PENALTY_MAP = {
        SeverityLevel.FATAL: 100,      # Total disqualification
        SeverityLevel.HIGH: 20,        # -20 points per weight
        SeverityLevel.MEDIUM: 10,      # -10 points per weight
        SeverityLevel.LOW: 5,          # -5 points per weight
    }

    def resolve_constraints(
        self,
        language: str,
        constraints: List[Constraint],
        requirements: Dict[str, Any],
    ) -> Tuple[VerdictLevel, int, str, List[str]]:
        """
        Resolve all constraints for a language against requirements

        Returns:
            (verdict_level, score_adjustment, reasoning, matching_constraint_keys)
        """
        # Step 1: Find all matching constraints
        matching_constraints = []
        for constraint in constraints:
            if constraint.matches(requirements):
                matching_constraints.append(constraint)

        if not matching_constraints:
            return VerdictLevel.SAFE, 0, "No conflicting constraints", []

        # Step 2: Sort by severity (highest first)
        matching_constraints.sort(
            key=lambda c: self.SEVERITY_RANK[c.severity],
            reverse=True
        )

        # Step 3: Get the worst constraint
        worst_constraint = matching_constraints[0]

        # Step 4: Calculate verdict and penalty
        verdict = self.SEVERITY_TO_VERDICT[worst_constraint.severity]

        if worst_constraint.severity == SeverityLevel.FATAL:
            score_adjustment = -100
            reasoning = f"Fatal constraint violated: {worst_constraint.reason[0] if worst_constraint.reason else 'constraint violation'}"
        else:
            # Calculate cumulative score adjustment
            score_adjustment = 0
            for constraint in matching_constraints:
                penalty = self.PENALTY_MAP[constraint.severity]
                score_adjustment -= penalty * constraint.weight

            reasoning = self._generate_reasoning(matching_constraints)

        # Step 5: Collect matching constraint keys
        matching_keys = [
            f"{c.key}={c.value}" for c in matching_constraints
        ]

        return verdict, score_adjustment, reasoning, matching_keys

    def _generate_reasoning(self, constraints: List[Constraint]) -> str:
        """Generate human-readable reasoning for constraint resolution"""
        if not constraints:
            return "No constraints violated"

        # Group by severity
        by_severity = {}
        for constraint in constraints:
            severity = constraint.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(constraint)

        reasons = []
        for severity in [SeverityLevel.FATAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
            if severity in by_severity:
                for constraint in by_severity[severity]:
                    reason_text = constraint.reason[0] if constraint.reason else f"{constraint.key} constraint violated"
                    reasons.append(f"[{severity.value}] {reason_text}")

        return "; ".join(reasons)

    def calculate_score(
        self,
        base_score: int,
        constraint_adjustments: int,
        capability_scores: int,
    ) -> int:
        """
        Calculate final score with adjustments

        Args:
            base_score: Starting score (typically 100)
            constraint_adjustments: Score changes from constraints (usually negative)
            capability_scores: Score changes from capabilities (usually positive)

        Returns:
            Final score clamped between 0 and 100
        """
        final_score = base_score + constraint_adjustments + capability_scores
        return max(0, min(100, final_score))

    def get_verdict_from_score(self, score: int) -> VerdictLevel:
        """Determine verdict level from score"""
        if score == 0:
            return VerdictLevel.FORBIDDEN
        elif score < 50:
            return VerdictLevel.CAUTION
        elif score < 80:
            return VerdictLevel.SAFE
        else:
            return VerdictLevel.OPTIMAL

    def score_capability(
        self,
        capability_name: str,
        strength: str,
        weight: float = 1.0,
    ) -> int:
        """Calculate score adjustment for a capability"""
        strength_map = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1,
        }
        base_points = strength_map.get(strength, 0)
        return int(base_points * weight)

    def apply_penalty(
        self,
        current_score: int,
        severity: SeverityLevel,
        weight: float = 1.0,
    ) -> int:
        """Apply penalty to score based on constraint severity"""
        penalty = self.PENALTY_MAP[severity]
        adjustment = -int(penalty * weight)
        return max(0, min(100, current_score + adjustment))
