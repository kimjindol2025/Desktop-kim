"""
Pattern Vector DB API v2.0
Language Vector Standard 기반 질의 엔진

핵심 원칙:
1. Cosine Similarity → 추천 순서 (top-K candidates)
2. Constraint Checking → 최종 GO/NOGO 판정
3. 책임 있는 AI 대답 (fatal은 절대 안 됨)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
import json
import math
from enum import Enum

# ============================================================================
# 데이터 모델
# ============================================================================

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FATAL = "fatal"


class ConstraintCondition(BaseModel):
    """제약 조건"""
    key: str
    value: str
    description: Optional[str] = None


class Constraint(BaseModel):
    """언어 제약 벡터"""
    language: str
    forbidden_when: Dict[str, Any]
    reason: List[str]
    severity: Severity
    alternatives: List[str] = []
    exceptions: List[str] = []


class Capability(BaseModel):
    """언어 가능성 벡터"""
    language: str
    capability: str
    description: str
    ir_dimension: str
    strength: Literal["low", "medium", "high"]
    confidence: float


class LanguageVector(BaseModel):
    """언어 벡터 (통합)"""
    language: str
    version: str
    dimensions: Dict[str, Any]
    capabilities: List[Capability] = []
    constraints: List[Constraint] = []


class VerdictResult(BaseModel):
    """최종 판정 결과"""
    language: str
    verdict: Literal["safe", "caution", "risky", "forbidden"]
    confidence: float
    reasons: List[str]
    recommendations: List[str]
    alternatives: Optional[List[str]] = None
    severity: Optional[Severity] = None


class LanguageQueryRequest(BaseModel):
    """언어 질의 요청"""
    language: str
    requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="What does the task require? e.g., {'execution_model': 'hard_realtime'}"
    )
    constraints: Optional[Dict[str, str]] = None


class ComparisonRequest(BaseModel):
    """언어 비교 요청"""
    languages: List[str] = Field(..., min_items=2, max_items=5)
    requirements: Dict[str, str]


# ============================================================================
# 제약 조건 정규화 (Phase 9.1)
# ============================================================================

class ConstraintKeyNormalizer:
    """제약 조건의 키를 정규화하여 일관성 보장"""

    KEY_ALIASES = {
        # 실행 모델 관련
        "execution_model": "execution_requirement",
        "exec_model": "execution_requirement",
        "exec_requirement": "execution_requirement",
        "execution": "execution_requirement",

        # 메모리 관련
        "memory_model": "memory_requirement",
        "mem_model": "memory_requirement",
        "memory": "memory_requirement",

        # 목표/용도 관련
        "target": "use_case",
        "purpose": "use_case",
        "domain": "use_case",

        # 성능 관련
        "performance": "performance_requirement",
        "perf": "performance_requirement",
    }

    @classmethod
    def normalize(cls, requirements: Dict[str, str]) -> Dict[str, str]:
        """요구사항 키를 정규화된 형식으로 변환"""
        if not requirements:
            return {}

        normalized = {}
        for key, value in requirements.items():
            # 정규화된 키 찾기 (없으면 원래 키 사용)
            canonical_key = cls.KEY_ALIASES.get(key, key)
            normalized[canonical_key] = value

        return normalized


# ============================================================================
# 벡터 로더
# ============================================================================

class LanguageVectorDB:
    """언어 벡터 데이터베이스"""

    def __init__(self, vectors_file: str = "/app/LANGUAGE_VECTORS_COMPLETE.jsonl"):
        self.vectors = {}
        self.constraints_by_language = {}
        self.capabilities_by_language = {}
        self.load_vectors(vectors_file)

    def load_vectors(self, filepath: str):
        """JSONL 파일에서 벡터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        language = data.get('language')

                        if data.get('vector_type') == 'constraint':
                            if language not in self.constraints_by_language:
                                self.constraints_by_language[language] = []
                            self.constraints_by_language[language].append(data)

                        elif data.get('vector_type') == 'capability':
                            if language not in self.capabilities_by_language:
                                self.capabilities_by_language[language] = []
                            self.capabilities_by_language[language].append(data)

                        elif data.get('vector_type') == 'language_core':
                            if language not in self.vectors:
                                self.vectors[language] = {}
                            self.vectors[language][data.get('dimension')] = data
        except FileNotFoundError:
            print(f"⚠️ Vector file not found: {filepath}")

    def check_constraints(self, language: str, requirements: Dict[str, str]) -> tuple[Severity, List[str], List[str]]:
        """
        언어가 요구사항을 충족할 수 있는지 확인

        Returns:
            (최악의 severity, 위반 이유들, 대안 언어들)
        """
        if language not in self.constraints_by_language:
            return Severity.LOW, [], []

        # Phase 9.1: 요구사항 키 정규화
        normalized_requirements = ConstraintKeyNormalizer.normalize(requirements)

        worst_severity = Severity.LOW
        reasons = []
        alternatives = set()

        for constraint in self.constraints_by_language[language]:
            forbidden_when = constraint.get('forbidden_when', {})
            # Phase 9.1: forbidden_when도 정규화
            normalized_forbidden = ConstraintKeyNormalizer.normalize(forbidden_when)

            # 요구사항과 금지조건 비교
            match_score = 0
            for key, value in normalized_forbidden.items():
                if key in normalized_requirements and normalized_requirements[key] == value:
                    match_score += 1

            # 일부라도 매치되면 제약 적용
            if match_score > 0:
                severity = Severity(constraint.get('severity', 'low'))
                reasons.extend(constraint.get('reason', []))

                # 최악의 severity 업데이트
                severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.FATAL]
                if severity_order.index(severity) > severity_order.index(worst_severity):
                    worst_severity = severity

                # 대안 수집
                alternatives.update(constraint.get('alternatives', []))

        return worst_severity, reasons, list(alternatives)

    def get_capabilities(self, language: str) -> List[str]:
        """언어의 가능성 목록 반환"""
        if language not in self.capabilities_by_language:
            return []
        return [c.get('capability') for c in self.capabilities_by_language[language]]


# ============================================================================
# FastAPI 애플리케이션
# ============================================================================

app = FastAPI(
    title="Pattern Vector DB API v2.0",
    description="Language Vector Standard 기반 AI 검증 시스템",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 벡터 DB 초기화
vector_db = LanguageVectorDB()

# ============================================================================
# 엔드포인트
# ============================================================================

@app.get("/api/v2/health", tags=["Health"])
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "languages_loaded": len(vector_db.vectors),
        "vector_db": "ready"
    }


@app.post("/api/v2/language/verdict", tags=["Verdict"], response_model=VerdictResult)
async def get_language_verdict(request: LanguageQueryRequest):
    """
    특정 언어가 요구사항을 충족할 수 있는지 판정

    Example:
        POST /api/v2/language/verdict
        {
            "language": "Python",
            "requirements": {
                "execution_model": "hard_realtime",
                "max_latency_ms": "1"
            }
        }

    Returns:
        - safe: 문제 없음
        - caution: 주의 필요
        - risky: 위험함
        - forbidden: 절대 안 됨 (fatal constraint)
    """
    language = request.language.strip()

    if language not in vector_db.vectors:
        raise HTTPException(
            status_code=404,
            detail=f"Language not found: {language}"
        )

    # Phase 9.1: 요구사항 정규화
    normalized_reqs = ConstraintKeyNormalizer.normalize(request.requirements)

    severity, reasons, alternatives = vector_db.check_constraints(
        language,
        normalized_reqs
    )

    # Verdict 결정
    verdict_map = {
        Severity.LOW: "safe",
        Severity.MEDIUM: "caution",
        Severity.HIGH: "risky",
        Severity.FATAL: "forbidden"
    }

    verdict = verdict_map[severity]
    confidence = 0.95 if severity == Severity.FATAL else 0.8

    recommendations = []
    if severity == Severity.FATAL:
        recommendations.append(f"🚫 {language}은(는) 이 요구사항을 충족할 수 없습니다")
        if alternatives:
            recommendations.append(f"✅ 대신 이 언어들을 추천합니다: {', '.join(alternatives)}")

    elif severity == Severity.HIGH:
        recommendations.append(f"⚠️ {language} 사용 시 심각한 문제 발생 가능")
        if alternatives:
            recommendations.append(f"💡 더 나은 선택지: {', '.join(alternatives)}")

    elif severity == Severity.MEDIUM:
        recommendations.append(f"⏸️ {language}은(는) 이 요구사항에 완벽하지 않습니다")
        recommendations.append("💭 검토 후 사용 결정 권장")

    else:
        recommendations.append(f"✅ {language}은(는) 이 요구사항을 충족합니다")

    return VerdictResult(
        language=language,
        verdict=verdict,
        confidence=confidence,
        reasons=reasons,
        recommendations=recommendations,
        alternatives=alternatives if alternatives else None,
        severity=severity
    )


@app.post("/api/v2/language/compare", tags=["Comparison"])
async def compare_languages(request: ComparisonRequest):
    """
    여러 언어 비교

    Example:
        POST /api/v2/language/compare
        {
            "languages": ["Rust", "Go", "Python"],
            "requirements": {
                "execution_model": "hard_realtime"
            }
        }

    Returns:
        각 언어별 verdict + 순위
    """
    # Phase 9.1: 요구사항 정규화
    normalized_reqs = ConstraintKeyNormalizer.normalize(request.requirements)

    results = []

    for language in request.languages:
        if language not in vector_db.vectors:
            results.append({
                "language": language,
                "status": "not_found",
                "error": f"Language not found: {language}"
            })
            continue

        severity, reasons, alternatives = vector_db.check_constraints(
            language,
            normalized_reqs
        )

        verdict_map = {
            Severity.LOW: "safe",
            Severity.MEDIUM: "caution",
            Severity.HIGH: "risky",
            Severity.FATAL: "forbidden"
        }

        results.append({
            "language": language,
            "verdict": verdict_map[severity],
            "severity": severity.value,
            "reasons": reasons,
            "alternatives": alternatives,
            "capabilities": vector_db.get_capabilities(language)[:5]
        })

    # Severity 기준 정렬 (safe가 먼저)
    severity_order = {"safe": 0, "caution": 1, "risky": 2, "forbidden": 3}
    results.sort(key=lambda x: severity_order.get(x.get("verdict", "forbidden"), 3))

    return {
        "requirements": request.requirements,
        "comparison": results,
        "recommendation": results[0]["language"] if results else None
    }


@app.get("/api/v2/language/{language}/details", tags=["Details"])
async def get_language_details(language: str):
    """
    언어의 상세 정보 조회

    Returns:
        - 기본 특성 (Language Vector)
        - 가능성 목록 (Capabilities)
        - 제약 목록 (Constraints)
    """
    language = language.strip()

    if language not in vector_db.vectors:
        raise HTTPException(
            status_code=404,
            detail=f"Language not found: {language}"
        )

    return {
        "language": language,
        "dimensions": vector_db.vectors[language],
        "capabilities": vector_db.capabilities_by_language.get(language, []),
        "constraints": vector_db.constraints_by_language.get(language, [])
    }


@app.get("/api/v2/languages", tags=["Catalog"])
async def list_languages():
    """지원하는 모든 언어 목록"""
    return {
        "total": len(vector_db.vectors),
        "languages": sorted(list(vector_db.vectors.keys()))
    }


@app.get("/api/v2/requirements/presets", tags=["Presets"])
async def get_requirement_presets():
    """일반적인 요구사항 프리셋"""
    presets = {
        "hard_realtime": {
            "execution_model": "hard_realtime",
            "max_latency_ms": "1",
            "deterministic": "required"
        },
        "low_latency_trading": {
            "execution_model": "financial_trading",
            "max_latency_ms": "100",
            "predictability": "critical"
        },
        "web_backend": {
            "execution_model": "web_server",
            "concurrency": "required",
            "memory_overhead": "acceptable"
        },
        "data_science": {
            "execution_model": "data_processing",
            "ecosystem": "rich_libraries",
            "speed_vs_dev_time": "dev_time"
        },
        "embedded_system": {
            "memory_model": "fixed_allocation",
            "performance": "critical",
            "power_consumption": "minimal"
        },
        "distributed_system": {
            "concurrency_model": "message_passing",
            "scalability": "horizontal",
            "fault_tolerance": "required"
        }
    }
    return presets


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
