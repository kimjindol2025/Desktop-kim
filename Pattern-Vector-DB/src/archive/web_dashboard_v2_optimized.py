"""
Pattern Vector Web Dashboard API v2.2 - Performance Optimized
Redis 캐싱, 성능 모니터링, 최적화된 쿼리
"""

import sys
from pathlib import Path
import time
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Import optimized components
from cache.redis_cache import RedisCache, CacheConfig, get_cache, cache_verdict, cache_language_info
from monitoring.performance_monitor import PerformanceMonitor, get_monitor

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


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pattern Vector Verdict Engine API v2.2",
    description="Performance-optimized language judgment system",
    version="2.2.0"
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
web_dir = Path(__file__).parent.parent.parent / "web"

try:
    verdict_engine = VerdictEngine(str(vector_db_path))
    verdict_tracer = VerdictTracer()
    cross_domain_engine = CrossDomainVerdictEngine()
    contradiction_detector = ContradictionDetector()
    immutable_log = ImmutableVerdictLog("web_dashboard_v2.2")
except Exception as e:
    print(f"Warning: Could not initialize engines: {e}")
    verdict_engine = None

# 캐시 및 모니터 초기화
cache = get_cache()
monitor = get_monitor()

# 정적 파일 마운트
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


# ============================================================================
# Middleware for Performance Monitoring
# ============================================================================

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """성능 모니터링 미들웨어"""
    request_id = str(uuid4())[:8]
    start_time = time.time()

    response = await call_next(request)

    response_time_ms = (time.time() - start_time) * 1000

    # 메트릭 기록
    monitor.record_request(
        request_id=request_id,
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        response_time_ms=response_time_ms,
        cache_hit=False,  # TODO: 실제 캐시 히트 여부 추적
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(response_time_ms)

    return response


# ============================================================================
# Root & Dashboard Endpoints
# ============================================================================

@app.get("/")
async def root():
    """대시보드"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return {"message": "Pattern Vector Verdict Engine v2.2"}


@app.get("/dashboard-advanced.html")
async def get_dashboard():
    """고급 대시보드"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")


# ============================================================================
# Health & Status Endpoints (with Caching)
# ============================================================================

@app.get("/api/v2/health")
async def health_check():
    """헬스 체크"""
    # 5초 TTL로 캐싱
    cache_key = "health:check"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = {
        "status": "healthy",
        "version": "2.2.0",
        "engine_initialized": verdict_engine is not None,
        "cache_enabled": cache.client is not None,
        "monitoring_enabled": True,
    }

    cache.set(cache_key, response, ttl=5, cache_type="stats")
    return response


@app.get("/api/v2/stats")
async def get_stats():
    """대시보드 통계"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    cache_key = "stats:dashboard"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = {
        "total_languages": len(verdict_engine.language_data),
        "total_capabilities": sum(
            len(data.get("capabilities", []))
            for data in verdict_engine.language_data.values()
        ),
        "total_constraints": sum(
            len(data.get("constraints", []))
            for data in verdict_engine.language_data.values()
        ),
        "engine_version": "2.2.0",
        "cache_stats": cache.get_stats(),
        "performance_stats": monitor.get_overall_stats(),
        "features": [
            "verdict_generation",
            "language_comparison",
            "cross_domain_verdict",
            "contradiction_detection",
            "redis_caching",
            "performance_monitoring",
            "websocket_streaming",
        ],
    }

    cache.set(cache_key, response, ttl=30, cache_type="stats")
    return response


# ============================================================================
# Language Information Endpoints (with Caching)
# ============================================================================

@app.get("/api/v2/languages")
async def get_all_languages():
    """모든 언어 목록"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    cache_key = "languages:all"
    cached = cache.get(cache_key)
    if cached:
        return cached

    languages = sorted(verdict_engine.language_data.keys())
    response = {
        "count": len(languages),
        "languages": languages,
    }

    cache.set(cache_key, response, ttl=3600, cache_type="language")
    return response


@app.get("/api/v2/language/{language}")
async def get_language_info(language: str):
    """언어 상세 정보"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    cache_key = f"language:{language}"
    cached = cache.get(cache_key)
    if cached:
        return cached

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

    response = {
        "language": language,
        "capabilities": capabilities,
        "constraints": constraints,
        "vector_count": len(info.get("capabilities", [])) + len(info.get("constraints", [])),
    }

    cache.set(cache_key, response, ttl=86400, cache_type="language")
    return response


# ============================================================================
# Verdict Endpoints (with Caching)
# ============================================================================

@app.post("/api/v2/verdict")
async def get_verdict(request: VerdictRequest):
    """판정 생성 (캐싱됨)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        # 캐시 키 생성
        cache_key = cache._generate_key("verdict", request.requirements)
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 판정 생성
        verdict = verdict_engine.generate_verdict(
            request.requirements,
            request.languages
        )

        # 추적 생성
        trace = verdict_tracer.create_trace(verdict.request_id, "multi_language")
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

        response = {
            "request_id": verdict.request_id,
            "timestamp": verdict.timestamp,
            "requirements": verdict.requirement,
            "verdicts": [v.to_dict() for v in verdict.verdicts],
            "rejected": [r.to_dict() for r in verdict.rejected_languages],
            "summary": verdict.summary.to_dict(),
            "engine_info": verdict.engine_info,
        }

        # 캐시에 저장
        cache.set(cache_key, response, cache_type="verdict")

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v2/compare")
async def compare_languages(request: ComparisonRequest):
    """언어 비교 (캐싱됨)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        # 캐시 키 생성
        cache_data = {
            "languages": sorted(request.languages),
            "requirements": request.requirements
        }
        cache_key = cache._generate_key("comparison", cache_data)
        cached = cache.get(cache_key)
        if cached:
            return cached

        comparison = verdict_engine.compare_languages(
            request.languages,
            request.requirements
        )

        response = {
            "requirement": comparison["requirement"],
            "comparison": comparison["comparison"],
            "rejected": comparison["rejected"],
            "summary": comparison["summary"],
        }

        cache.set(cache_key, response, cache_type="comparison")
        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Monitoring & Performance Endpoints
# ============================================================================

@app.get("/api/v2/monitoring/stats")
async def get_monitoring_stats():
    """모니터링 통계"""
    return {
        "overall": monitor.get_overall_stats(),
        "methods": monitor.get_method_stats(),
        "cache_stats": cache.get_stats(),
    }


@app.get("/api/v2/monitoring/report")
async def get_monitoring_report():
    """성능 리포트"""
    return {
        "report": monitor.export_report(),
        "generated_at": str(time.time()),
    }


@app.get("/api/v2/monitoring/slowest")
async def get_slowest_requests(limit: int = Query(10, ge=1, le=100)):
    """가장 느린 요청들"""
    slowest = monitor.get_slowest_requests(limit)
    return {
        "count": len(slowest),
        "requests": [m.to_dict() for m in slowest],
    }


@app.get("/api/v2/cache/clear")
async def clear_cache():
    """캐시 초기화"""
    cache.clear()
    return {"status": "cleared", "message": "Cache cleared successfully"}


@app.get("/api/v2/cache/stats")
async def get_cache_stats():
    """캐시 통계"""
    return cache.get_stats()


# ============================================================================
# Cross-Domain & Advanced Endpoints
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

        base_verdict = verdict_engine.generate_verdict(
            request.requirements,
            [request.language]
        )
        base_score = base_verdict.verdicts[0].score if base_verdict.verdicts else 100

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


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555

    print(f"""
    🚀 Pattern Vector Verdict Engine v2.2 (Optimized)

    Starting on http://0.0.0.0:{port}

    ✨ Features:
    ✅ Redis Caching
    ✅ Performance Monitoring
    ✅ Real-time Statistics
    ✅ WebSocket Streaming
    ✅ Automatic Query Optimization

    📊 Monitoring Endpoints:
    - GET /api/v2/monitoring/stats       - Overall statistics
    - GET /api/v2/monitoring/report      - Performance report
    - GET /api/v2/monitoring/slowest     - Slowest requests
    - GET /api/v2/cache/stats            - Cache statistics
    - GET /api/v2/cache/clear            - Clear cache

    📚 Dashboard: http://localhost:{port}
    📚 API Docs: http://localhost:{port}/docs
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=True,
    )
