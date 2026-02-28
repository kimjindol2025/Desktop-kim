"""
Pattern Vector DB API Server
FastAPI 기반 REST API 서버

엔드포인트:
  POST   /api/v1/patterns/search       - 패턴 검색
  GET    /api/v1/patterns/{lang}/{op}  - 특정 패턴 조회
  POST   /api/v1/patterns/batch        - 배치 검색
  GET    /api/v1/stats                 - 통계 조회
  GET    /api/v1/health                - 헬스 체크
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Pattern Vector DB API",
    description="AI-native pattern validation and recommendation system",
    version="0.1.0-alpha",
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
# 데이터 모델
# ============================================================================

class PatternMetadata(BaseModel):
    """패턴 메타데이터"""
    performance: float = Field(..., ge=0.0, le=1.0)
    memory: float = Field(..., ge=0.0, le=1.0)
    concurrency: float = Field(..., ge=0.0, le=1.0)
    testing: float = Field(..., ge=0.0, le=1.0)
    ecosystem: float = Field(..., ge=0.0, le=1.0)
    real_world: float = Field(..., ge=0.0, le=1.0)
    best_practices: float = Field(..., ge=0.0, le=1.0)


class PatternSearchRequest(BaseModel):
    """패턴 검색 요청"""
    language: str = Field(..., description="프로그래밍 언어 (예: Ruby, Python)")
    operation: str = Field(..., description="연산 종류 (예: read.file, filter, parse.json)")
    context: Optional[str] = Field(None, description="추가 컨텍스트 (예: large files, streaming)")
    top_k: int = Field(5, ge=1, le=20, description="상위 K개 결과")


class PatternSearchResult(BaseModel):
    """패턴 검색 결과"""
    id: str
    language: str
    operation: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    safety_verdict: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    metadata: PatternMetadata
    recommendations: List[str]
    file_path: str


class BatchSearchRequest(BaseModel):
    """배치 검색 요청"""
    queries: List[PatternSearchRequest]


class StatsResponse(BaseModel):
    """통계 응답"""
    total_patterns: int
    languages: int
    operations: int
    avg_safety_score: float
    avg_performance_score: float


class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    version: str
    patterns_loaded: int


# ============================================================================
# 전역 상태
# ============================================================================

class PatternDB:
    """패턴 데이터베이스"""
    def __init__(self):
        self.patterns = []
        self.metadata_file = Path(__file__).parent.parent.parent / "pattern-vectors.jsonl"
        self.load_patterns()

    def load_patterns(self):
        """JSON Lines 파일에서 패턴 로드"""
        if not self.metadata_file.exists():
            logger.warning(f"메타데이터 파일 없음: {self.metadata_file}")
            return

        try:
            with open(self.metadata_file, 'r') as f:
                for line in f:
                    if line.strip():
                        self.patterns.append(json.loads(line))
            logger.info(f"✅ {len(self.patterns)}개 패턴 로드 완료")
        except Exception as e:
            logger.error(f"❌ 패턴 로드 오류: {e}")

    def search(self, language: str, operation: str, top_k: int = 5) -> List[dict]:
        """패턴 검색"""
        results = []

        for pattern in self.patterns:
            if (pattern.get('language') == language and
                pattern.get('operation') == operation):
                results.append(pattern)
                if len(results) >= top_k:
                    break

        return results

    def get_by_id(self, pattern_id: str) -> Optional[dict]:
        """ID로 패턴 조회"""
        for pattern in self.patterns:
            if pattern.get('id') == pattern_id:
                return pattern
        return None

    def get_stats(self) -> dict:
        """통계 계산"""
        languages = set()
        operations = set()
        total_safety = 0
        total_performance = 0
        count = 0

        for pattern in self.patterns:
            languages.add(pattern.get('language'))
            operations.add(pattern.get('operation'))

            metadata = pattern.get('metadata', {})
            total_safety += (metadata.get('best_practices', 0) +
                           metadata.get('concurrency', 0)) / 2
            total_performance += metadata.get('performance', 0)
            count += 1

        return {
            "total_patterns": len(self.patterns),
            "languages": len(languages),
            "operations": len(operations),
            "avg_safety_score": round(total_safety / count, 2) if count > 0 else 0,
            "avg_performance_score": round(total_performance / count, 2) if count > 0 else 0,
        }


# 전역 DB 인스턴스
db = PatternDB()


# ============================================================================
# API 엔드포인트
# ============================================================================

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    헬스 체크 엔드포인트

    서버 상태 확인
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0-alpha",
        patterns_loaded=len(db.patterns),
    )


@app.post("/api/v1/patterns/search", response_model=List[PatternSearchResult])
async def search_pattern(request: PatternSearchRequest):
    """
    패턴 검색 엔드포인트

    쿼리:
    ```json
    {
      "language": "Ruby",
      "operation": "read.file",
      "context": "large files, streaming",
      "top_k": 5
    }
    ```

    응답:
    ```json
    [
      {
        "id": "ruby-read.file-001",
        "language": "Ruby",
        "operation": "read.file",
        "similarity_score": 0.87,
        "safety_verdict": "caution",
        "overall_score": 0.75,
        "metadata": {...},
        "recommendations": ["Use streaming", "Handle EOF"],
        "file_path": "CodeMind/01_code_assets/io/read.file.rb"
      }
    ]
    ```
    """
    try:
        patterns = db.search(request.language, request.operation, request.top_k)

        if not patterns:
            raise HTTPException(
                status_code=404,
                detail=f"패턴을 찾을 수 없음: {request.language}/{request.operation}"
            )

        results = []
        for pattern in patterns:
            metadata = pattern.get('metadata', {})

            # 안전도 판정
            safety_score = (metadata.get('best_practices', 0) +
                          metadata.get('concurrency', 0)) / 2
            if safety_score >= 0.80:
                safety_verdict = "safe"
            elif safety_score >= 0.60:
                safety_verdict = "caution"
            else:
                safety_verdict = "risky"

            # 전체 점수
            overall = (metadata.get('performance', 0) * 0.3 +
                      metadata.get('best_practices', 0) * 0.3 +
                      metadata.get('ecosystem', 0) * 0.2 +
                      metadata.get('memory', 0) * 0.2)

            # 권장사항
            recommendations = []
            if metadata.get('performance', 0) < 0.75:
                recommendations.append("성능 최적화 권장")
            if metadata.get('memory', 0) < 0.75:
                recommendations.append("메모리 관리 검토 필요")
            if metadata.get('concurrency', 0) < 0.70:
                recommendations.append("동시성 안전도 확인 권장")
            if not recommendations:
                recommendations.append("권장되는 구현입니다")

            results.append(PatternSearchResult(
                id=pattern.get('id'),
                language=pattern.get('language'),
                operation=pattern.get('operation'),
                similarity_score=min(1.0, overall),
                safety_verdict=safety_verdict,
                overall_score=round(overall, 2),
                metadata=PatternMetadata(**metadata),
                recommendations=recommendations,
                file_path=pattern.get('file_path', ''),
            ))

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검색 오류: {e}")
        raise HTTPException(status_code=500, detail="검색 중 오류 발생")


@app.get("/api/v1/patterns/{language}/{operation}")
async def get_pattern(language: str, operation: str):
    """
    특정 패턴 조회

    경로 파라미터:
      - language: 언어 (예: Ruby)
      - operation: 연산 (예: read.file)
    """
    try:
        patterns = db.search(language, operation, 1)

        if not patterns:
            raise HTTPException(
                status_code=404,
                detail=f"패턴을 찾을 수 없음: {language}/{operation}"
            )

        pattern = patterns[0]
        return {
            "id": pattern.get('id'),
            "language": pattern.get('language'),
            "operation": pattern.get('operation'),
            "file_path": pattern.get('file_path'),
            "lines_of_code": pattern.get('lines_of_code'),
            "metadata": pattern.get('metadata'),
            "error_codes": pattern.get('error_codes'),
            "complexity": pattern.get('complexity'),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"조회 오류: {e}")
        raise HTTPException(status_code=500, detail="조회 중 오류 발생")


@app.post("/api/v1/patterns/batch")
async def batch_search(request: BatchSearchRequest):
    """
    배치 검색 (여러 패턴 한 번에 검색)

    쿼리:
    ```json
    {
      "queries": [
        {"language": "Ruby", "operation": "read.file"},
        {"language": "Python", "operation": "filter"},
        {"language": "Go", "operation": "parse.json"}
      ]
    }
    ```
    """
    try:
        results = {}

        for query in request.queries:
            key = f"{query.language}/{query.operation}"
            patterns = db.search(query.language, query.operation, query.top_k)

            if patterns:
                pattern = patterns[0]
                metadata = pattern.get('metadata', {})
                overall = (metadata.get('performance', 0) * 0.3 +
                          metadata.get('best_practices', 0) * 0.3 +
                          metadata.get('ecosystem', 0) * 0.2 +
                          metadata.get('memory', 0) * 0.2)

                results[key] = {
                    "found": True,
                    "id": pattern.get('id'),
                    "overall_score": round(overall, 2),
                    "metadata": metadata,
                }
            else:
                results[key] = {
                    "found": False,
                    "message": "패턴을 찾을 수 없음"
                }

        return results

    except Exception as e:
        logger.error(f"배치 검색 오류: {e}")
        raise HTTPException(status_code=500, detail="배치 검색 중 오류 발생")


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """
    통계 조회

    응답:
    ```json
    {
      "total_patterns": 60,
      "languages": 20,
      "operations": 3,
      "avg_safety_score": 0.78,
      "avg_performance_score": 0.85
    }
    ```
    """
    try:
        stats = db.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류 발생")


# ============================================================================
# 루트 엔드포인트
# ============================================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "Pattern Vector DB API",
        "version": "0.1.0-alpha",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /api/v1/health",
            "search": "POST /api/v1/patterns/search",
            "get": "GET /api/v1/patterns/{language}/{operation}",
            "batch": "POST /api/v1/patterns/batch",
            "stats": "GET /api/v1/stats",
        }
    }


# ============================================================================
# 에러 핸들러
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 핸들러"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Pattern Vector DB API 서버 시작")
    print("📖 API 문서: http://localhost:8000/docs")
    print("📊 통계: http://localhost:8000/api/v1/stats")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
