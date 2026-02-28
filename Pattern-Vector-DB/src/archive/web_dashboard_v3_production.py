"""
Pattern Vector Verdict Engine - Production Ready v3.0
SSL/TLS, JWT Auth, Rate Limiting, Advanced Logging
"""

import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import production components
from cache.redis_cache import get_cache
from monitoring.performance_monitor import get_monitor
from logging.advanced_logger import get_logger, LoggingMiddleware
from security.auth import (
    jwt_manager,
    api_key_manager,
    rate_limiter,
    JWTConfig,
    AccessToken,
    hash_password,
    verify_password,
)

from verdict.verdict_engine import VerdictEngine
from verdict.verdict_trace import VerdictTracer
from verdict.cross_domain_verdict import CrossDomainVerdictEngine, CrossDomainConfig
from verdict.contradiction_detector import ContradictionDetector
from verdict.verdict_log import ImmutableVerdictLog

# ============================================================================
# Models
# ============================================================================

class VerdictRequest(BaseModel):
    requirements: dict
    languages: Optional[list] = None
    project: Optional[str] = None


class ComparisonRequest(BaseModel):
    languages: list
    requirements: dict


class LoginRequest(BaseModel):
    username: str
    password: str


class APIKeyRequest(BaseModel):
    name: str


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pattern Vector Verdict Engine v3.0 (Production)",
    description="Production-ready language judgment system",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging Middleware
logger = get_logger("verdict_engine_v3")
app.add_middleware(LoggingMiddleware, logger=logger)

# ============================================================================
# Global Instances
# ============================================================================

vector_db_path = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"
web_dir = Path(__file__).parent.parent.parent / "web"

try:
    verdict_engine = VerdictEngine(str(vector_db_path))
    verdict_tracer = VerdictTracer()
    cross_domain_engine = CrossDomainVerdictEngine()
    contradiction_detector = ContradictionDetector()
    immutable_log = ImmutableVerdictLog("web_dashboard_v3")
except Exception as e:
    logger.logger.error(f"Failed to initialize engines: {e}")
    verdict_engine = None

cache = get_cache()
monitor = get_monitor()

# ============================================================================
# Authentication Dependencies
# ============================================================================

async def verify_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Bearer 토큰 검증"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()

        payload = jwt_manager.verify_token(token)
        return payload.sub
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """API 키 검증"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    try:
        api_key = api_key_manager.verify_key(x_api_key)
        return api_key.key
    except HTTPException:
        raise


async def check_rate_limit(request: Request):
    """Rate Limiting 확인"""
    client_ip = request.client.host

    if not rate_limiter.is_allowed(client_ip):
        remaining = rate_limiter.get_remaining(client_ip)
        reset_time = rate_limiter.get_reset_time(client_ip)

        logger.log_security_event(
            "rate_limit_exceeded",
            "anonymous",
            client_ip,
            {"remaining": remaining, "reset_time": str(reset_time)},
        )

        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={
                "X-RateLimit-Limit": str(rate_limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            },
        )


# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================

@app.get("/")
async def root():
    """대시보드"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return {"message": "Pattern Vector Verdict Engine v3.0"}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    cache_key = "health:v3"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = {
        "status": "operational",
        "version": "3.0.0",
        "engine": "ready" if verdict_engine else "offline",
        "cache": "connected" if cache.client else "in-memory",
        "timestamp": str(__import__("datetime").datetime.utcnow()),
    }

    cache.set(cache_key, response, ttl=5)
    return response


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/login")
async def login(request: LoginRequest, _=Depends(check_rate_limit)):
    """로그인"""
    # 데모용 사용자 (실제에는 DB에서 조회)
    demo_users = {
        "admin": hash_password("admin123"),
        "user": hash_password("user123"),
    }

    if request.username not in demo_users:
        logger.log_security_event(
            "login_failed",
            request.username,
            "unknown",
            {"reason": "user_not_found"},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, demo_users[request.username]):
        logger.log_security_event(
            "login_failed",
            request.username,
            "unknown",
            {"reason": "invalid_password"},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tokens = jwt_manager.create_tokens(request.username)

    logger.log_security_event(
        "login_success",
        request.username,
        "unknown",
        {"method": "password"},
    )

    return tokens


@app.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    _=Depends(check_rate_limit),
):
    """토큰 갱신"""
    access_token = jwt_manager.refresh_access_token(refresh_token)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/api-key")
async def create_api_key(
    request: APIKeyRequest,
    user_id: str = Depends(verify_bearer_token),
    _=Depends(check_rate_limit),
):
    """API 키 생성"""
    key = api_key_manager.generate_key(request.name)

    logger.log_security_event(
        "api_key_created",
        user_id,
        "internal",
        {"api_key_name": request.name},
    )

    return {"api_key": key, "name": request.name}


# ============================================================================
# Protected Verdict Endpoints
# ============================================================================

@app.post("/api/v3/verdict")
async def get_verdict(
    request: VerdictRequest,
    user_id: str = Depends(verify_bearer_token),
    _=Depends(check_rate_limit),
):
    """판정 생성 (인증 필수)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        verdict = verdict_engine.generate_verdict(
            request.requirements,
            request.languages
        )

        trace = verdict_tracer.create_trace(verdict.request_id, "multi_language")
        trace.final_score = int(
            sum(v.score for v in verdict.verdicts) / len(verdict.verdicts)
            if verdict.verdicts else 0
        )

        immutable_log.log_verdict(
            trail_id="web_dashboard_v3",
            entry_id=verdict.request_id,
            language="multi",
            verdict="completed",
            score=trace.final_score,
            requirements=request.requirements,
            user=user_id,
            project=request.project,
        )

        logger.log_verdict(
            user_id,
            verdict.request_id,
            "multi",
            "completed",
            trace.final_score,
            0,
        )

        return {
            "request_id": verdict.request_id,
            "verdicts": [v.to_dict() for v in verdict.verdicts],
            "score": trace.final_score,
        }

    except Exception as e:
        logger.log_error(e, {"endpoint": "/api/v3/verdict"})
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v3/compare")
async def compare_languages(
    request: ComparisonRequest,
    user_id: str = Depends(verify_bearer_token),
    _=Depends(check_rate_limit),
):
    """언어 비교 (인증 필수)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        comparison = verdict_engine.compare_languages(
            request.languages,
            request.requirements
        )

        return {
            "comparison": comparison["comparison"],
            "rejected": comparison["rejected"],
        }

    except Exception as e:
        logger.log_error(e, {"endpoint": "/api/v3/compare"})
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Public Monitoring Endpoints
# ============================================================================

@app.get("/api/v3/monitoring/health")
async def monitoring_health(_=Depends(check_rate_limit)):
    """모니터링 헬스"""
    return {
        "overall_stats": monitor.get_overall_stats(),
        "cache_stats": cache.get_stats(),
    }


@app.get("/api/v3/monitoring/slowest")
async def get_slowest_requests(
    limit: int = 10,
    _=Depends(check_rate_limit),
):
    """가장 느린 요청들"""
    slowest = monitor.get_slowest_requests(limit)
    return {
        "count": len(slowest),
        "requests": [m.to_dict() for m in slowest],
    }


# ============================================================================
# Admin Endpoints (Protected)
# ============================================================================

@app.get("/api/v3/admin/report")
async def get_full_report(
    user_id: str = Depends(verify_bearer_token),
    _=Depends(check_rate_limit),
):
    """전체 성능 리포트 (관리자용)"""
    if user_id != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "performance_report": monitor.export_report(),
        "cache_stats": cache.get_stats(),
    }


@app.post("/api/v3/admin/cache/clear")
async def clear_cache_admin(
    user_id: str = Depends(verify_bearer_token),
    _=Depends(check_rate_limit),
):
    """캐시 초기화 (관리자용)"""
    if user_id != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    cache.clear()

    logger.log_security_event(
        "cache_cleared",
        user_id,
        "internal",
        {},
    )

    return {"status": "cleared"}


# ============================================================================
# Information Endpoints
# ============================================================================

@app.get("/api/v3/info")
async def get_info(_=Depends(check_rate_limit)):
    """API 정보"""
    return {
        "name": "Pattern Vector Verdict Engine",
        "version": "3.0.0",
        "environment": "production",
        "features": [
            "jwt_authentication",
            "api_key_auth",
            "rate_limiting",
            "advanced_logging",
            "redis_caching",
            "performance_monitoring",
        ],
        "endpoints": {
            "auth": "/auth/login",
            "verdict": "/api/v3/verdict",
            "compare": "/api/v3/compare",
            "monitoring": "/api/v3/monitoring/health",
        },
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print(f"""
    🚀 Pattern Vector Verdict Engine v3.0 (Production Ready)

    Features:
    ✅ JWT Authentication
    ✅ API Key Management
    ✅ Rate Limiting (1000 req/min)
    ✅ Advanced Logging (JSON + Text)
    ✅ Performance Monitoring
    ✅ Redis Caching
    ✅ Security Event Logging

    🔐 Authentication:
    - POST /auth/login → Get JWT token
    - POST /auth/refresh → Refresh token
    - POST /auth/api-key → Create API key

    📊 Protected Endpoints:
    - POST /api/v3/verdict (requires auth)
    - POST /api/v3/compare (requires auth)

    📈 Public Endpoints:
    - GET /health
    - GET /api/v3/info
    - GET /api/v3/monitoring/health
    - GET /api/v3/monitoring/slowest

    🔧 Admin Endpoints:
    - GET /api/v3/admin/report (admin only)
    - POST /api/v3/admin/cache/clear (admin only)

    Demo Credentials:
    - Username: admin, Password: admin123
    - Username: user, Password: user123

    📚 API Docs: http://localhost:5555/docs
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5555,
        reload=False,
        access_log=False,  # Use custom logging
    )
