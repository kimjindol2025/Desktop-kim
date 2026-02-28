"""
Pattern Vector Web Dashboard API v2
FastAPI 기반 웹 대시보드 백엔드 + WebSocket 지원
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
import json
import asyncio
from datetime import datetime

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


class StreamRequest(BaseModel):
    """스트리밍 요청"""
    requirements: Dict[str, Any]
    languages: Optional[List[str]] = None


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pattern Vector Verdict Engine API v2",
    description="AI-powered language judgment system with WebSocket & real-time updates",
    version="2.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트 (web 디렉토리)
web_dir = Path(__file__).parent.parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

# ============================================================================
# 글로벌 인스턴스
# ============================================================================

vector_db_path = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"

try:
    verdict_engine = VerdictEngine(str(vector_db_path))
    verdict_tracer = VerdictTracer()
    cross_domain_engine = CrossDomainVerdictEngine()
    contradiction_detector = ContradictionDetector()
    immutable_log = ImmutableVerdictLog("web_dashboard_v2")
except Exception as e:
    print(f"Warning: Could not initialize engines: {e}")
    verdict_engine = None


# ============================================================================
# WebSocket Manager
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")


manager = ConnectionManager()


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/api/v2/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "engine_initialized": verdict_engine is not None,
        "timestamp": datetime.now().isoformat(),
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
        "engine_version": "2.1.0",
        "features": [
            "verdict_trace",
            "cross_domain_verdict",
            "contradiction_detection",
            "immutable_log",
            "websocket_streaming",
            "advanced_filtering",
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


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/verdict")
async def websocket_verdict(websocket: WebSocket):
    """WebSocket 판정 스트리밍"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "verdict_request":
                try:
                    # 판정 생성
                    verdict = verdict_engine.generate_verdict(
                        data.get("requirements", {}),
                        data.get("languages")
                    )

                    # 각 언어의 판정을 스트리밍으로 전송
                    for v in verdict.verdicts:
                        await websocket.send_json({
                            "type": "verdict_result",
                            "language": v.language,
                            "verdict": v.verdict,
                            "score": v.score,
                            "reasoning": v.reasoning,
                        })

                    # 완료 메시지
                    await websocket.send_json({
                        "type": "verdict_complete",
                        "request_id": verdict.request_id,
                        "total_evaluated": len(verdict.verdicts),
                        "total_rejected": len(verdict.rejected_languages),
                    })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket 실시간 스트림"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "subscribe_stats":
                # 주기적으로 통계 전송
                while True:
                    stats = await get_stats()
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": stats,
                        "timestamp": datetime.now().isoformat(),
                    })
                    await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# Streaming Verdict Endpoint
# ============================================================================

@app.post("/api/v2/verdict/stream")
async def stream_verdict(request: VerdictRequest):
    """스트리밍 판정 생성 (Server-Sent Events)"""
    if not verdict_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    async def generate():
        try:
            verdict = verdict_engine.generate_verdict(
                request.requirements,
                request.languages
            )

            for v in verdict.verdicts:
                yield f"data: {json.dumps({'type': 'verdict', 'language': v.language, 'verdict': v.verdict, 'score': v.score})}\n\n"
                await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'type': 'complete', 'request_id': verdict.request_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return generate()


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
            "entries": [e.to_dict() for e in trail.entries[-10:]],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v2/trace/{verdict_id}")
async def get_trace(verdict_id: str):
    """판정 추적 조회"""
    trace = verdict_tracer.get_trace(verdict_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {verdict_id}")

    return trace.to_dict()


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """대시보드 (Advanced Dashboard)"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")

    # Fallback: API info
    return {
        "name": "Pattern Vector Verdict Engine v2.1",
        "version": "2.1.0",
        "status": "operational",
        "features": [
            "verdict_generation",
            "language_comparison",
            "cross_domain_verdict",
            "contradiction_detection",
            "immutable_audit_trail",
            "verdict_trace",
            "websocket_streaming",
            "server_sent_events",
        ],
        "docs": "/docs",
        "api_prefix": "/api/v2",
        "websocket_endpoints": [
            "/ws/verdict",
            "/ws/stream",
        ],
    }

@app.get("/dashboard-advanced.html")
async def get_dashboard():
    """고급 대시보드"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/dashboard")
async def get_dashboard_redirect():
    """대시보드 리다이렉트"""
    dashboard_file = web_dir / "dashboard-advanced.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import sys

    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555

    print(f"""
    🚀 Pattern Vector Verdict Engine Web Dashboard v2.1

    Starting on http://0.0.0.0:{port}

    📚 Dashboard: http://localhost:{port}
    📚 API Docs: http://localhost:{port}/docs
    🔄 ReDoc: http://localhost:{port}/redoc

    🌐 Advanced Dashboard:
    - http://localhost:{port}/dashboard-advanced.html
    - http://localhost:{port}/dashboard

    🔗 WebSocket Endpoints:
    - WS /ws/verdict       - Real-time verdict streaming
    - WS /ws/stream        - Live stats streaming

    Available REST Endpoints:
    - GET  /api/v2/health          - Health check
    - GET  /api/v2/stats           - Dashboard stats
    - GET  /api/v2/languages       - All languages
    - POST /api/v2/verdict         - Generate verdict
    - POST /api/v2/compare         - Compare languages
    - POST /api/v2/cross-domain/verdict - Cross-domain verdict
    - GET  /api/v2/rules/validate  - Validate rules
    - GET  /api/v2/audit/trail     - Audit trail
    - POST /api/v2/verdict/stream  - Server-Sent Events streaming
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=True,
    )
