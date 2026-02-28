"""
Pattern Vector Verdict Engine - Simple v3.0 (No Auth Required)
"""

import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import components
try:
    from verdict.verdict_engine import VerdictEngine
    from verdict.verdict_trace import VerdictTracer
    from verdict.contradiction_detector import ContradictionDetector
    from verdict.verdict_log import ImmutableVerdictLog
except Exception as e:
    print(f"⚠️  Import Warning: {e}")

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

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pattern Vector Verdict Engine v3.0 (Simple)",
    description="Language judgment system - No Auth",
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

# ============================================================================
# Global Instances
# ============================================================================

vector_db_path = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"
web_dir = Path(__file__).parent.parent.parent / "web"

try:
    verdict_engine = VerdictEngine(str(vector_db_path))
    verdict_tracer = VerdictTracer()
    contradiction_detector = ContradictionDetector()
    immutable_log = ImmutableVerdictLog("web_dashboard_v3_simple")
    print("✅ 엔진 초기화 완료")
except Exception as e:
    print(f"⚠️  엔진 초기화 실패: {e}")
    verdict_engine = None

# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================

@app.get("/")
async def root():
    """대시보드"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return {
        "message": "Pattern Vector Verdict Engine v3.0 (Simple)",
        "status": "ready",
        "version": "3.0.0"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "operational",
        "version": "3.0.0",
        "engine": "ready" if verdict_engine else "offline",
        "timestamp": str(__import__("datetime").datetime.utcnow()),
    }

@app.get("/api/v3/info")
async def get_info():
    """API 정보"""
    return {
        "name": "Pattern Vector Verdict Engine",
        "version": "3.0.0",
        "environment": "simple (no auth)",
        "features": [
            "verdict_generation",
            "language_comparison",
            "performance_monitoring",
            "advanced_logging",
        ],
        "endpoints": {
            "verdict": "/api/v3/verdict",
            "compare": "/api/v3/compare",
            "monitoring": "/api/v3/monitoring/health",
        },
    }

# ============================================================================
# Verdict Endpoints (No Auth Required)
# ============================================================================

@app.post("/api/v3/verdict")
async def get_verdict(request: VerdictRequest):
    """판정 생성 (인증 불필요)"""
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
            trail_id="web_dashboard_v3_simple",
            entry_id=verdict.request_id,
            language="multi",
            verdict="completed",
            score=trace.final_score,
            requirements=request.requirements,
            reasoning="Multi-language verdict generated via API",
            user="anonymous",
            project=request.project,
        )

        return {
            "request_id": verdict.request_id,
            "verdicts": [v.to_dict() for v in verdict.verdicts],
            "score": trace.final_score,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v3/compare")
async def compare_languages(request: ComparisonRequest):
    """언어 비교 (인증 불필요)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        comparison = verdict_engine.compare_languages(
            request.languages,
            request.requirements
        )

        return {
            "comparison": comparison["comparison"],
            "rejected": comparison.get("rejected", []),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# Monitoring Endpoints
# ============================================================================

@app.get("/api/v3/monitoring/health")
async def monitoring_health():
    """모니터링 헬스"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": str(__import__("datetime").datetime.utcnow()),
    }

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print(f"""
    🚀 Pattern Vector Verdict Engine v3.0 (Simple - No Auth)
    
    Features:
    ✅ No Authentication Required
    ✅ Verdict Generation
    ✅ Language Comparison
    ✅ Performance Monitoring
    ✅ Advanced Logging
    
    📊 Endpoints:
    - POST /api/v3/verdict (판정 생성)
    - POST /api/v3/compare (언어 비교)
    - GET  /health (헬스체크)
    - GET  /api/v3/info (API 정보)
    - GET  /api/v3/monitoring/health
    
    📚 API Docs: http://localhost:5555/docs
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5555,
        reload=False,
        access_log=False,
    )
