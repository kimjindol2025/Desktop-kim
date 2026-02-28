"""
Pattern Vector Verdict Engine v1.0

Main engine that orchestrates language verdict generation
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .verdict_types import (
    Verdict, VerdictLevel, Constraint, Capability,
    VerdictDSLRule, FinalVerdict, LanguageVerdict,
    RejectedLanguage, VerdictSummary, SeverityLevel,
)
from .constraint_resolver import ConstraintResolver
from .verdict_dsl_parser import VerdictDSLParser


class VerdictEngine:
    """
    AI-powered verdict engine for language selection

    Evaluates languages against requirements using:
    1. Constraint-based filtering (must-pass rules)
    2. Capability-based scoring (nice-to-have features)
    3. Verdict DSL rules (explicit judgment rules)
    """

    def __init__(self, vector_db_path: Optional[str] = None):
        """Initialize verdict engine"""
        self.constraints_resolver = ConstraintResolver()
        self.dsl_parser = VerdictDSLParser()
        self.dsl_rules: Dict[str, VerdictDSLRule] = {}
        self.language_data: Dict[str, Dict[str, Any]] = {}

        if vector_db_path:
            self.load_language_vectors(vector_db_path)

    def load_language_vectors(self, vector_db_path: str) -> None:
        """Load language vectors from JSONL file"""
        if not Path(vector_db_path).exists():
            raise FileNotFoundError(f"Vector DB not found: {vector_db_path}")

        with open(vector_db_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                    vector_type = entry.get("vector_type") or entry.get("type")

                    if vector_type == "language_core":
                        language = entry.get("language")
                        if language not in self.language_data:
                            self.language_data[language] = {
                                "capabilities": [],
                                "constraints": [],
                                "metadata": entry,
                            }

                    elif vector_type == "capability":
                        language = entry.get("language")
                        if language:
                            # Initialize language if not exists
                            if language not in self.language_data:
                                self.language_data[language] = {
                                    "capabilities": [],
                                    "constraints": [],
                                    "metadata": {},
                                }

                            self.language_data[language]["capabilities"].append(
                                Capability(
                                    name=entry.get("capability") or entry.get("name"),
                                    strength=entry.get("strength", "medium"),
                                    weight=entry.get("weight", 1.0),
                                    confidence=entry.get("confidence", 0.95),
                                )
                            )

                    elif vector_type == "constraint":
                        language = entry.get("language")
                        if language:
                            # Initialize language if not exists
                            if language not in self.language_data:
                                self.language_data[language] = {
                                    "capabilities": [],
                                    "constraints": [],
                                    "metadata": {},
                                }

                            # forbidden_when is a dict like {"target": "rapid_prototyping"}
                            # For each key-value pair, create a constraint
                            forbidden_when = entry.get("forbidden_when", {})
                            if isinstance(forbidden_when, dict):
                                for key, value in forbidden_when.items():
                                    self.language_data[language]["constraints"].append(
                                        Constraint(
                                            key=key,
                                            value=str(value),
                                            severity=SeverityLevel(
                                                entry.get("severity", "medium")
                                            ),
                                            weight=entry.get("weight", 1.0),
                                            reason=entry.get("reason", []),
                                            alternatives=entry.get("alternatives", []),
                                            confidence=entry.get("confidence", 0.95),
                                        )
                                    )
                except json.JSONDecodeError:
                    continue

    def load_verdict_dsl_rules(self, rules_file: str) -> None:
        """Load Verdict DSL rules from file"""
        self.dsl_rules = self.dsl_parser.parse_rules_from_file(rules_file)

    def add_dsl_rule(self, rule: VerdictDSLRule) -> None:
        """Add a single DSL rule"""
        self.dsl_rules[rule.rule_id] = rule

    def generate_verdict(
        self,
        requirements: Dict[str, Any],
        languages: Optional[List[str]] = None,
    ) -> FinalVerdict:
        """
        Generate final verdict for given requirements

        Args:
            requirements: Dictionary of requirements and constraints
            languages: Specific languages to evaluate (None = all loaded)

        Returns:
            FinalVerdict with complete analysis
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Normalize requirements
        normalized_req = self._normalize_requirements(requirements)

        # Determine languages to evaluate
        if languages is None:
            languages = list(self.language_data.keys())

        # Evaluate each language
        verdicts: List[LanguageVerdict] = []
        rejected: List[RejectedLanguage] = []

        for language in languages:
            if language not in self.language_data:
                continue

            lang_data = self.language_data[language]
            constraints = lang_data.get("constraints", [])
            capabilities = lang_data.get("capabilities", [])

            # Resolve constraints
            verdict_level, score_adj, reasoning, matching_constraints = (
                self.constraints_resolver.resolve_constraints(
                    language, constraints, normalized_req
                )
            )

            # Check if rejected (fatal constraint)
            if verdict_level == VerdictLevel.FORBIDDEN and score_adj == -100:
                rejected.append(
                    RejectedLanguage(
                        language=language,
                        reason=reasoning,
                        fatal_constraint=matching_constraints[0] if matching_constraints else None,
                    )
                )
                continue

            # Calculate capability scores
            capability_score = self._calculate_capability_score(
                capabilities, normalized_req
            )
            matching_capabilities = [
                cap.name for cap in capabilities
                if cap.name in normalized_req.get("required_capabilities", [])
            ]

            # Calculate final score
            final_score = self.constraints_resolver.calculate_score(
                100, score_adj, capability_score
            )

            # Determine verdict level from score
            final_verdict = self.constraints_resolver.get_verdict_from_score(
                final_score
            )

            # Create language verdict
            lang_verdict = LanguageVerdict(
                language=language,
                verdict=final_verdict,
                score=final_score,
                reasoning=reasoning,
                constraints_checked=len(constraints),
                constraints_passed=len(constraints) - len(matching_constraints),
                matching_constraints=matching_constraints,
                matching_capabilities=matching_capabilities,
            )

            verdicts.append(lang_verdict)

        # Sort by score (descending)
        verdicts.sort(key=lambda v: v.score, reverse=True)

        # Generate summary
        summary = VerdictSummary(
            total_evaluated=len(languages),
            rejected=len(rejected),
            caution=sum(1 for v in verdicts if v.verdict == VerdictLevel.CAUTION),
            safe=sum(1 for v in verdicts if v.verdict == VerdictLevel.SAFE),
            optimal=sum(1 for v in verdicts if v.verdict == VerdictLevel.OPTIMAL),
        )

        # Engine info
        execution_time_ms = int((time.time() - start_time) * 1000)
        engine_info = {
            "version": "1.0.0",
            "rules_applied": len(self.dsl_rules),
            "languages_evaluated": len(languages),
            "constraints_checked": sum(v.constraints_checked for v in verdicts),
            "confidence": self._calculate_confidence(verdicts),
            "execution_time_ms": execution_time_ms,
        }

        return FinalVerdict(
            request_id=request_id,
            timestamp=timestamp,
            requirement=normalized_req,
            verdicts=verdicts,
            rejected_languages=rejected,
            summary=summary,
            engine_info=engine_info,
        )

    def _normalize_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize requirement keys to standard format"""
        normalized = {}

        # Direct mappings
        key_mappings = {
            "execution_model": "execution_requirement",
            "execution_req": "execution_requirement",
            "realtime": "execution_requirement",
            "memory": "memory_limit",
            "deployment_target": "target",
        }

        for key, value in requirements.items():
            # Apply mapping if exists
            normalized_key = key_mappings.get(key, key)
            normalized[normalized_key] = value

        return normalized

    def _calculate_capability_score(
        self,
        capabilities: List[Capability],
        requirements: Dict[str, Any],
    ) -> int:
        """Calculate score bonus from matching capabilities"""
        score = 0
        required_capabilities = requirements.get("required_capabilities", [])

        for capability in capabilities:
            if capability.name in required_capabilities:
                points = capability.score_value()
                score += int(points * capability.weight)

        return score

    def _calculate_confidence(self, verdicts: List[LanguageVerdict]) -> float:
        """Calculate overall confidence in verdicts"""
        if not verdicts:
            return 0.0

        # Average confidence from all verdicts
        total_confidence = 0.0
        for verdict in verdicts:
            # Use matching capabilities and constraints to determine confidence
            total_matches = (
                len(verdict.matching_capabilities)
                + len(verdict.matching_constraints)
            )
            confidence = (
                0.95
                if total_matches == 0
                else 0.85 + (0.1 * min(total_matches, 2) / 2)
            )
            total_confidence += confidence

        return min(0.99, total_confidence / len(verdicts))

    def compare_languages(
        self,
        languages: List[str],
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare specific languages against requirements

        Returns comparison data showing how each language scores
        """
        verdict = self.generate_verdict(requirements, languages)

        return {
            "requirement": verdict.requirement,
            "comparison": [v.to_dict() for v in verdict.verdicts],
            "rejected": [r.to_dict() for r in verdict.rejected_languages],
            "summary": verdict.summary.to_dict(),
        }

    def recommend_languages(
        self,
        requirements: Dict[str, Any],
        top_n: int = 5,
    ) -> List[str]:
        """
        Recommend top N languages for given requirements

        Returns list of language names ordered by recommendation strength
        """
        verdict = self.generate_verdict(requirements)

        # Filter by verdict level (optimal, then safe, then caution)
        optimal = [
            v.language for v in verdict.verdicts
            if v.verdict == VerdictLevel.OPTIMAL
        ]
        safe = [
            v.language for v in verdict.verdicts
            if v.verdict == VerdictLevel.SAFE
        ]
        caution = [
            v.language for v in verdict.verdicts
            if v.verdict == VerdictLevel.CAUTION
        ]

        recommendations = optimal + safe + caution
        return recommendations[:top_n]

    def get_verdict_report(self, verdict: FinalVerdict) -> str:
        """Generate human-readable verdict report"""
        report_lines = [
            "=" * 70,
            "PATTERN VECTOR VERDICT ENGINE - FINAL REPORT",
            "=" * 70,
            f"\nRequest ID: {verdict.request_id}",
            f"Timestamp: {verdict.timestamp}",
            f"\nRequirements:",
        ]

        for key, value in verdict.requirement.items():
            report_lines.append(f"  {key}: {value}")

        report_lines.extend([
            f"\n{'-' * 70}",
            f"SUMMARY",
            f"{'-' * 70}",
            f"Total Evaluated:  {verdict.summary.total_evaluated}",
            f"Rejected:         {verdict.summary.rejected}",
            f"Caution:          {verdict.summary.caution}",
            f"Safe:             {verdict.summary.safe}",
            f"Optimal:          {verdict.summary.optimal}",
        ])

        if verdict.verdicts:
            report_lines.extend([
                f"\n{'-' * 70}",
                f"RECOMMENDATIONS",
                f"{'-' * 70}",
            ])

            for i, v in enumerate(verdict.verdicts[:10], 1):
                report_lines.append(
                    f"\n{i}. {v.language} ({v.verdict.value.upper()})"
                )
                report_lines.append(f"   Score: {v.score}/100")
                report_lines.append(f"   Reasoning: {v.reasoning}")

        if verdict.rejected_languages:
            report_lines.extend([
                f"\n{'-' * 70}",
                f"REJECTED LANGUAGES",
                f"{'-' * 70}",
            ])

            for r in verdict.rejected_languages[:5]:
                report_lines.append(f"\n✗ {r.language}")
                report_lines.append(f"  Reason: {r.reason}")
                if r.fatal_constraint:
                    report_lines.append(f"  Fatal Constraint: {r.fatal_constraint}")

        report_lines.extend([
            f"\n{'-' * 70}",
            f"ENGINE INFO",
            f"{'-' * 70}",
            f"Version: {verdict.engine_info.get('version')}",
            f"Execution Time: {verdict.engine_info.get('execution_time_ms')}ms",
            f"Confidence: {verdict.engine_info.get('confidence'):.1%}",
            f"Languages Evaluated: {verdict.engine_info.get('languages_evaluated')}",
        ])

        return "\n".join(report_lines)
