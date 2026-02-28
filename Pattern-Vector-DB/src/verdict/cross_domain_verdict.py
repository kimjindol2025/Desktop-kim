"""
Cross-Domain Verdict System

멀티 도메인 판정 - "Rust + Linux + ARM + RT" 같은 복합 환경 지원
언어 + 런타임 + OS + 하드웨어 + 프레임워크의 조합 판정
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class DomainType(Enum):
    """도메인 타입"""
    LANGUAGE = "language"           # 프로그래밍 언어
    RUNTIME = "runtime"             # 런타임 (JVM, CLR, Node.js 등)
    OS = "os"                        # 운영체제
    HARDWARE = "hardware"            # 하드웨어 (ARM, x86, GPU 등)
    FRAMEWORK = "framework"          # 프레임워크
    DEPLOYMENT = "deployment"        # 배포 환경


@dataclass
class DomainConstraint:
    """도메인별 제약"""
    domain: DomainType
    component: str                   # 구체적인 컴포넌트 (e.g., "Linux", "ARM", "JVM")
    severity: str
    reason: List[str]
    incompatible_with: List[Tuple[DomainType, str]] = field(default_factory=list)  # 호환 불가능

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain.value,
            "component": self.component,
            "severity": self.severity,
            "reason": self.reason,
            "incompatible_with": [
                (d.value, c) for d, c in self.incompatible_with
            ],
        }


@dataclass
class DomainCapability:
    """도메인별 능력"""
    domain: DomainType
    component: str
    capability: str
    strength: str

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain.value,
            "component": self.component,
            "capability": self.capability,
            "strength": self.strength,
        }


@dataclass
class CrossDomainConfig:
    """멀티 도메인 설정"""
    language: str
    runtime: Optional[str] = None
    os: Optional[str] = None
    hardware: Optional[str] = None
    framework: Optional[str] = None
    deployment: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "language": self.language,
            "runtime": self.runtime,
            "os": self.os,
            "hardware": self.hardware,
            "framework": self.framework,
            "deployment": self.deployment,
        }

    def __str__(self) -> str:
        """예: "Rust + Linux + ARM + RT"""
        parts = [self.language]
        if self.runtime:
            parts.append(self.runtime)
        if self.os:
            parts.append(self.os)
        if self.hardware:
            parts.append(self.hardware)
        if self.framework:
            parts.append(self.framework)
        if self.deployment:
            parts.append(self.deployment)
        return " + ".join(parts)


@dataclass
class CrossDomainVerdictResult:
    """멀티 도메인 판정 결과"""
    config: CrossDomainConfig
    verdict: str                    # "optimal", "safe", "caution", "forbidden"
    score: int
    reasoning: str

    # 도메인별 분석
    language_verdict: Optional[str] = None
    runtime_verdict: Optional[str] = None
    os_verdict: Optional[str] = None
    hardware_verdict: Optional[str] = None
    framework_verdict: Optional[str] = None

    # 호환성 검사
    compatibility_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 통계
    domains_evaluated: int = 0
    constraints_checked: int = 0
    constraints_passed: int = 0

    def to_dict(self) -> Dict:
        return {
            "config": self.config.to_dict(),
            "verdict": self.verdict,
            "score": self.score,
            "reasoning": self.reasoning,
            "domain_verdicts": {
                "language": self.language_verdict,
                "runtime": self.runtime_verdict,
                "os": self.os_verdict,
                "hardware": self.hardware_verdict,
                "framework": self.framework_verdict,
            },
            "compatibility": {
                "issues": self.compatibility_issues,
                "warnings": self.warnings,
            },
            "statistics": {
                "domains_evaluated": self.domains_evaluated,
                "constraints_checked": self.constraints_checked,
                "constraints_passed": self.constraints_passed,
            },
        }


class CrossDomainVerdictEngine:
    """멀티 도메인 판정 엔진"""

    def __init__(self):
        # 도메인별 제약과 능력
        self.domain_data: Dict[DomainType, Dict[str, Any]] = {
            domain: {"constraints": [], "capabilities": []}
            for domain in DomainType
        }

        # 호환성 규칙
        self.compatibility_rules: List[Tuple[
            Tuple[DomainType, str],
            Tuple[DomainType, str],
            str
        ]] = []

        self._init_compatibility_rules()

    def _init_compatibility_rules(self) -> None:
        """호환성 규칙 초기화"""
        # 예시: Rust + Linux + ARM은 최적 조합
        # Python + Hard Realtime + ARM은 불가능

        incompatible_combos = [
            # (언어, 하드웨어) 조합 불가능
            ("Python", "hard_realtime"),
            ("Java", "hard_realtime"),
            ("C#", "hard_realtime"),

            # (런타임, OS) 조합 불가능
            ("JVM", "bare_metal"),
            ("CLR", "Linux"),

            # (프레임워크, 하드웨어) 조합 불가능
            ("Django", "microcontroller"),
            ("Spring", "FPGA"),
        ]

        for lang, hw in incompatible_combos:
            self.compatibility_rules.append((
                (DomainType.LANGUAGE, lang),
                (DomainType.HARDWARE, hw),
                "fatal"
            ))

    def evaluate_cross_domain(
        self,
        config: CrossDomainConfig,
        base_verdict_score: int = 100,
    ) -> CrossDomainVerdictResult:
        """
        멀티 도메인 판정 평가

        Args:
            config: 크로스 도메인 설정
            base_verdict_score: 기본 점수 (언어 기본 판정에서)

        Returns:
            CrossDomainVerdictResult
        """
        result = CrossDomainVerdictResult(
            config=config,
            verdict="safe",
            score=base_verdict_score,
            reasoning="",
        )

        current_score = base_verdict_score
        domains_evaluated = 0
        constraints_checked = 0

        # 1. 호환성 검사
        incompatibilities = self._check_compatibility(config)
        if incompatibilities:
            for issue in incompatibilities:
                result.compatibility_issues.append(issue)
                current_score -= 50  # 큰 감점

            if any("fatal" in issue for issue in incompatibilities):
                result.verdict = "forbidden"
                current_score = 0

        # 2. 도메인별 제약 검사
        if config.runtime:
            domains_evaluated += 1
            runtime_issues = self._evaluate_runtime(config.runtime)
            constraints_checked += len(runtime_issues["constraints"])
            current_score -= runtime_issues["penalty"]
            result.runtime_verdict = runtime_issues["verdict"]

        if config.os:
            domains_evaluated += 1
            os_issues = self._evaluate_os(config.os)
            constraints_checked += len(os_issues["constraints"])
            current_score -= os_issues["penalty"]
            result.os_verdict = os_issues["verdict"]

        if config.hardware:
            domains_evaluated += 1
            hw_issues = self._evaluate_hardware(config.hardware)
            constraints_checked += len(hw_issues["constraints"])
            current_score -= hw_issues["penalty"]
            result.hardware_verdict = hw_issues["verdict"]

        if config.framework:
            domains_evaluated += 1
            fw_issues = self._evaluate_framework(config.framework)
            constraints_checked += len(fw_issues["constraints"])
            current_score -= fw_issues["penalty"]
            result.framework_verdict = fw_issues["verdict"]

        if config.deployment:
            domains_evaluated += 1
            dp_issues = self._evaluate_deployment(config.deployment)
            constraints_checked += len(dp_issues["constraints"])
            current_score -= dp_issues["penalty"]

        # 3. 최종 점수 및 판정 결정
        result.score = max(0, min(100, current_score))
        result.domains_evaluated = domains_evaluated
        result.constraints_checked = constraints_checked

        # 판정 레벨 결정
        if result.score == 0:
            result.verdict = "forbidden"
        elif result.score < 50:
            result.verdict = "caution"
        elif result.score < 80:
            result.verdict = "safe"
        else:
            result.verdict = "optimal"

        # 추론 생성
        result.reasoning = self._generate_reasoning(result)

        return result

    def _check_compatibility(self, config: CrossDomainConfig) -> List[str]:
        """호환성 검사"""
        issues = []

        # 언어 + 런타임 호환성
        if config.language and config.runtime:
            incompatible = self._is_incompatible(
                config.language, config.runtime
            )
            if incompatible:
                issues.append(
                    f"FATAL: {config.language} + {config.runtime} incompatible"
                )

        # 런타임 + OS 호환성
        if config.runtime and config.os:
            incompatible = self._is_incompatible(
                config.runtime, config.os
            )
            if incompatible:
                issues.append(
                    f"WARNING: {config.runtime} may not work well on {config.os}"
                )

        # 하드웨어 + OS 호환성
        if config.hardware and config.os:
            if not self._is_hardware_os_compatible(config.hardware, config.os):
                issues.append(
                    f"WARNING: {config.hardware} + {config.os} compatibility needed"
                )

        return issues

    def _is_incompatible(self, domain1: str, domain2: str) -> bool:
        """두 도메인 컴포넌트 호환성 확인"""
        # 단순화된 호환성 규칙
        incompatible_pairs = [
            ("Python", "hard_realtime"),
            ("Java", "hard_realtime"),
            ("JVM", "bare_metal"),
            ("Django", "microcontroller"),
        ]

        return (domain1, domain2) in incompatible_pairs or \
               (domain2, domain1) in incompatible_pairs

    def _is_hardware_os_compatible(self, hardware: str, os: str) -> bool:
        """하드웨어-OS 호환성"""
        compatible_pairs = [
            ("ARM", "Linux"),
            ("ARM", "bare_metal"),
            ("x86", "Linux"),
            ("x86", "Windows"),
            ("GPU", "Linux"),
            ("GPU", "Windows"),
        ]

        return (hardware, os) in compatible_pairs

    def _evaluate_runtime(self, runtime: str) -> Dict[str, Any]:
        """런타임 평가"""
        # 런타임별 평가 규칙
        runtime_scores = {
            "JVM": {"verdict": "safe", "penalty": 10, "constraints": ["jvm_overhead"]},
            "CLR": {"verdict": "safe", "penalty": 8, "constraints": ["dotnet_overhead"]},
            "Node.js": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "Python": {"verdict": "safe", "penalty": 5, "constraints": ["interpreter_overhead"]},
            "LLVM": {"verdict": "optimal", "penalty": 0, "constraints": []},
        }
        return runtime_scores.get(runtime, {"verdict": "safe", "penalty": 0, "constraints": []})

    def _evaluate_os(self, os: str) -> Dict[str, Any]:
        """OS 평가"""
        os_scores = {
            "Linux": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "Windows": {"verdict": "safe", "penalty": 5, "constraints": ["windows_compat"]},
            "macOS": {"verdict": "safe", "penalty": 5, "constraints": ["macos_compat"]},
            "bare_metal": {"verdict": "optimal", "penalty": 0, "constraints": []},
        }
        return os_scores.get(os, {"verdict": "safe", "penalty": 0, "constraints": []})

    def _evaluate_hardware(self, hardware: str) -> Dict[str, Any]:
        """하드웨어 평가"""
        hw_scores = {
            "ARM": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "x86": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "GPU": {"verdict": "safe", "penalty": 10, "constraints": ["gpu_overhead"]},
            "FPGA": {"verdict": "optimal", "penalty": 0, "constraints": []},
        }
        return hw_scores.get(hardware, {"verdict": "safe", "penalty": 0, "constraints": []})

    def _evaluate_framework(self, framework: str) -> Dict[str, Any]:
        """프레임워크 평가"""
        fw_scores = {
            "Django": {"verdict": "safe", "penalty": 10, "constraints": ["django_overhead"]},
            "FastAPI": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "Spring": {"verdict": "safe", "penalty": 5, "constraints": ["spring_overhead"]},
            "React": {"verdict": "optimal", "penalty": 0, "constraints": []},
        }
        return fw_scores.get(framework, {"verdict": "safe", "penalty": 0, "constraints": []})

    def _evaluate_deployment(self, deployment: str) -> Dict[str, Any]:
        """배포 환경 평가"""
        dep_scores = {
            "cloud": {"verdict": "optimal", "penalty": 0, "constraints": []},
            "edge": {"verdict": "safe", "penalty": 5, "constraints": ["edge_constraint"]},
            "embedded": {"verdict": "safe", "penalty": 10, "constraints": ["embedded_constraint1", "embedded_constraint2"]},
            "bare_metal": {"verdict": "optimal", "penalty": 0, "constraints": []},
        }
        return dep_scores.get(deployment, {"verdict": "safe", "penalty": 0, "constraints": []})

    def _generate_reasoning(self, result: CrossDomainVerdictResult) -> str:
        """추론 생성"""
        parts = [f"Configuration: {result.config}"]

        if result.compatibility_issues:
            parts.append(f"Compatibility issues: {len(result.compatibility_issues)}")
            for issue in result.compatibility_issues:
                parts.append(f"  - {issue}")

        if result.warnings:
            parts.append(f"Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                parts.append(f"  - {warning}")

        parts.append(f"Score: {result.score}/100")
        parts.append(f"Verdict: {result.verdict}")

        return "\n".join(parts)

    def recommend_configuration(
        self,
        requirements: Dict[str, Any],
        language: str,
    ) -> CrossDomainConfig:
        """
        요구사항에 맞는 크로스 도메인 구성 추천

        Args:
            requirements: 요구사항 (e.g., {"realtime": True, "edge_deployment": True})
            language: 기본 언어

        Returns:
            추천 구성
        """
        config = CrossDomainConfig(language=language)

        # 하드 리얼타임이면 Linux + LLVM
        if requirements.get("hard_realtime"):
            config.os = "Linux"
            config.runtime = "LLVM"
            config.hardware = "x86"

        # 엣지 배포면 ARM
        if requirements.get("edge_deployment"):
            config.hardware = "ARM"
            config.deployment = "edge"

        # 클라우드면 Docker/Kubernetes
        if requirements.get("cloud"):
            config.deployment = "cloud"
            config.os = "Linux"

        return config
