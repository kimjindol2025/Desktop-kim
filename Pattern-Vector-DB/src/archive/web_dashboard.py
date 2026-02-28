"""
Pattern Vector Web Dashboard API

FastAPI 기반 웹 대시보드 백엔드
React 프론트엔드와 통합
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verdict.verdict_engine import VerdictEngine
from verdict.verdict_trace import VerdictTracer
from verdict.cross_domain_verdict import CrossDomainVerdictEngine, CrossDomainConfig
from verdict.contradiction_detector import ContradictionDetector
from verdict.verdict_log import ImmutableVerdictLog

# ============================================================================
# Request/Response Models
# ============================================================================

class VerdictRequest(BaseModel):
    """판정 요청"""
    requirements: Dict[str, Any]
    languages: Optional[List[str]] = None
    project: Optional[str] = None
    user: Optional[str] = None


class ComparisonRequest(BaseModel):
    """언어 비교 요청"""
    languages: List[str]
    requirements: Dict[str, Any]


class CrossDomainRequest(BaseModel):
    """크로스 도메인 판정 요청"""
    language: str
    runtime: Optional[str] = None
    os: Optional[str] = None
    hardware: Optional[str] = None
    framework: Optional[str] = None
    deployment: Optional[str] = None
    requirements: Dict[str, Any]


class DashboardStats(BaseModel):
    """대시보드 통계"""
    total_languages: int
    total_verdicts_today: int
    most_recommended: Optional[str]
    most_rejected: Optional[str]
    engine_version: str
    uptime_hours: float


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pattern Vector Verdict Engine API",
    description="AI-powered language judgment system with web dashboard",
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

# ============================================================================
# 글로벌 인스턴스
# ============================================================================

vector_db_path = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"

try:
    verdict_engine = VerdictEngine(str(vector_db_path))
    verdict_tracer = VerdictTracer()
    cross_domain_engine = CrossDomainVerdictEngine()
    contradiction_detector = ContradictionDetector()
    immutable_log = ImmutableVerdictLog("web_dashboard")
except Exception as e:
    print(f"Warning: Could not initialize engines: {e}")
    verdict_engine = None

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/api/v2/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "engine_initialized": verdict_engine is not None,
    }


@app.get("/api/v2/stats")
async def get_stats():
    """대시보드 통계"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    return {
        "total_languages": len(verdict_engine.language_data),
        "total_capabilities": sum(
            len(data.get("capabilities", []))
            for data in verdict_engine.language_data.values()
        ),
        "total_constraints": sum(
            len(data.get("constraints", []))
            for data in verdict_engine.language_data.values()
        ),
        "engine_version": "2.0.0",
        "features": [
            "verdict_trace",
            "cross_domain_verdict",
            "contradiction_detection",
            "immutable_log"
        ],
    }


# ============================================================================
# Language Information Endpoints
# ============================================================================

@app.get("/api/v2/languages")
async def get_all_languages():
    """모든 언어 목록"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    languages = sorted(verdict_engine.language_data.keys())
    return {
        "count": len(languages),
        "languages": languages,
    }


@app.get("/api/v2/language/{language}")
async def get_language_info(language: str):
    """언어 상세 정보"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    info = verdict_engine.language_data.get(language)
    if not info:
        raise HTTPException(status_code=404, detail=f"Language not found: {language}")

    capabilities = [
        {"name": c.name, "strength": c.strength}
        for c in info.get("capabilities", [])
    ]
    constraints = [
        {"key": c.key, "value": c.value, "severity": c.severity.value}
        for c in info.get("constraints", [])
    ]

    return {
        "language": language,
        "capabilities": capabilities,
        "constraints": constraints,
        "vector_count": len(info.get("capabilities", [])) + len(info.get("constraints", [])),
    }


# ============================================================================
# Verdict Endpoints
# ============================================================================

@app.post("/api/v2/verdict")
async def get_verdict(request: VerdictRequest):
    """판정 생성"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        # 판정 생성
        verdict = verdict_engine.generate_verdict(
            request.requirements,
            request.languages
        )

        # 추적 생성
        trace = verdict_tracer.create_trace(
            verdict.request_id,
            "multi_language"
        )
        trace.requirement_normalization = request.requirements
        trace.final_score = int(
            sum(v.score for v in verdict.verdicts) / len(verdict.verdicts)
            if verdict.verdicts else 0
        )

        # 로그에 기록
        immutable_log.log_verdict(
            trail_id="web_dashboard",
            entry_id=verdict.request_id,
            language="multi",
            verdict="completed",
            score=trace.final_score,
            requirements=request.requirements,
            reasoning=f"Evaluated {len(verdict.verdicts)} languages",
            user=request.user,
            project=request.project,
        )

        return {
            "request_id": verdict.request_id,
            "timestamp": verdict.timestamp,
            "requirements": verdict.requirement,
            "verdicts": [v.to_dict() for v in verdict.verdicts],
            "rejected": [r.to_dict() for r in verdict.rejected_languages],
            "summary": verdict.summary.to_dict(),
            "engine_info": verdict.engine_info,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v2/compare")
async def compare_languages(request: ComparisonRequest):
    """언어 비교"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        comparison = verdict_engine.compare_languages(
            request.languages,
            request.requirements
        )

        return {
            "requirement": comparison["requirement"],
            "comparison": comparison["comparison"],
            "rejected": comparison["rejected"],
            "summary": comparison["summary"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v2/recommend")
async def recommend_languages(
    requirements: Dict[str, Any] = Query(...),
    top_n: int = Query(5, ge=1, le=50)
):
    """언어 추천"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        recommendations = verdict_engine.recommend_languages(requirements, top_n)

        return {
            "requirements": requirements,
            "count": len(recommendations),
            "recommendations": recommendations,
            "top_n": top_n,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Cross-Domain Endpoints
# ============================================================================

@app.post("/api/v2/cross-domain/verdict")
async def cross_domain_verdict(request: CrossDomainRequest):
    """크로스 도메인 판정"""
    try:
        config = CrossDomainConfig(
            language=request.language,
            runtime=request.runtime,
            os=request.os,
            hardware=request.hardware,
            framework=request.framework,
            deployment=request.deployment,
        )

        # 기본 판정 점수 조회
        base_verdict = verdict_engine.generate_verdict(
            request.requirements,
            [request.language]
        )
        base_score = base_verdict.verdicts[0].score if base_verdict.verdicts else 100

        # 크로스 도메인 평가
        result = cross_domain_engine.evaluate_cross_domain(config, base_score)

        return {
            "config": result.config.to_dict(),
            "verdict": result.verdict,
            "score": result.score,
            "reasoning": result.reasoning,
            "domain_verdicts": {
                "language": result.language_verdict,
                "runtime": result.runtime_verdict,
                "os": result.os_verdict,
                "hardware": result.hardware_verdict,
                "framework": result.framework_verdict,
            },
            "compatibility": {
                "issues": result.compatibility_issues,
                "warnings": result.warnings,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v2/cross-domain/recommend")
async def recommend_cross_domain_config(
    language: str = Query(...),
    requirements: Dict[str, Any] = Query(...)
):
    """크로스 도메인 구성 추천"""
    try:
        config = cross_domain_engine.recommend_configuration(requirements, language)

        return {
            "recommended_config": config.to_dict(),
            "configuration_string": str(config),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Contradiction Detection Endpoints
# ============================================================================

@app.get("/api/v2/rules/validate")
async def validate_rules():
    """규칙 검증"""
    try:
        result = contradiction_detector.validate_all_rules()

        return {
            "valid": result.is_valid,
            "conflicts": [c.to_dict() for c in result.conflicts],
            "warnings": result.warnings,
            "statistics": result.stats,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v2/rules/report")
async def get_contradiction_report():
    """모순 보고서"""
    try:
        result = contradiction_detector.validate_all_rules()
        report = contradiction_detector.get_conflict_report(result)

        return {
            "report": report,
            "valid": result.is_valid,
            "conflict_count": len(result.conflicts),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Audit Trail Endpoints
# ============================================================================

@app.get("/api/v2/audit/trail")
async def get_audit_trail():
    """감사 추적 조회"""
    try:
        trail = immutable_log.get_trail("web_dashboard")
        if not trail:
            return {
                "trail_id": "web_dashboard",
                "entries": [],
                "integrity": True,
            }

        return {
            "trail_id": trail.trail_id,
            "created_at": trail.created_at,
            "entry_count": len(trail.entries),
            "integrity_verified": trail.verify_chain_integrity(),
            "entries": [e.to_dict() for e in trail.entries[-10:]],  # 최근 10개
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v2/audit/report")
async def get_audit_report():
    """감사 보고서"""
    try:
        report = immutable_log.generate_audit_report("web_dashboard")
        compliance = immutable_log.generate_compliance_report("web_dashboard")

        return {
            "audit_report": report,
            "compliance_report": compliance,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Trace Endpoints
# ============================================================================

@app.get("/api/v2/trace/{verdict_id}")
async def get_trace(verdict_id: str):
    """판정 추적 조회"""
    trace = verdict_tracer.get_trace(verdict_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {verdict_id}")

    return trace.to_dict()


@app.get("/api/v2/trace/{verdict_id}/report")
async def get_trace_report(verdict_id: str):
    """판정 추적 보고서"""
    trace = verdict_tracer.get_trace(verdict_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {verdict_id}")

    report = trace.to_markdown_report()
    return {
        "verdict_id": verdict_id,
        "report": report,
    }


# ============================================================================
# Search Endpoints (from Search API)
# ============================================================================

@app.get("/api/v2/search/name")
async def search_by_name(q: str = Query(...), limit: int = Query(10, ge=1, le=50)):
    """언어명 검색"""
    # Import search API if available
    try:
        from search.vector_db import VectorDB
        db = VectorDB(str(vector_db_path))
        results = db.search_by_name(q, limit)

        return {
            "query": q,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v2/search/capability")
async def search_by_capability(
    capability: str = Query(...),
    limit: int = Query(10, ge=1, le=50)
):
    """능력으로 검색"""
    try:
        from search.vector_db import VectorDB
        db = VectorDB(str(vector_db_path))
        results = db.search_by_capability(capability, limit)

        return {
            "capability": capability,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "Pattern Vector Verdict Engine",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "verdict_generation",
            "language_comparison",
            "recommendation",
            "cross_domain_verdict",
            "contradiction_detection",
            "immutable_audit_trail",
            "verdict_trace",
        ],
        "docs": "/docs",
        "api_prefix": "/api/v2",
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
    🚀 Pattern Vector Verdict Engine Web Dashboard

    Starting on http://0.0.0.0:8000

    📚 API Docs: http://localhost:8000/docs
    🔄 ReDoc: http://localhost:8000/redoc

    Available Endpoints:
    - GET  /api/v2/health          - Health check
    - GET  /api/v2/stats           - Dashboard stats
    - GET  /api/v2/languages       - All languages
    - POST /api/v2/verdict         - Generate verdict
    - POST /api/v2/compare         - Compare languages
    - POST /api/v2/recommend       - Recommend languages
    - POST /api/v2/cross-domain/verdict - Cross-domain verdict
    - GET  /api/v2/audit/trail     - Audit trail
    - GET  /api/v2/trace/{id}      - Verdict trace
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
