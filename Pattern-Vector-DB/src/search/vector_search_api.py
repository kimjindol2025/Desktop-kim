"""
벡터 DB 검색 API
50개 언어 데이터 검색 및 필터링
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import os
from pathlib import Path
import numpy as np
from difflib import SequenceMatcher

app = FastAPI(title="Vector DB Search API", version="1.0.0")

# Load vector data
VECTOR_FILE = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"

class VectorDB:
    """벡터 데이터베이스"""
    
    def __init__(self, filepath):
        self.languages = {}
        self.load_data(filepath)
    
    def load_data(self, filepath):
        """JSONL 파일에서 데이터 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    lang = data.get('language')
                    
                    if lang not in self.languages:
                        self.languages[lang] = {
                            'language_core': [],
                            'capabilities': [],
                            'constraints': []
                        }
                    
                    vector_type = data.get('vector_type')
                    if vector_type == 'language_core':
                        self.languages[lang]['language_core'].append(data)
                    elif vector_type == 'capability':
                        self.languages[lang]['capabilities'].append(data.get('capability'))
                    elif vector_type == 'constraint':
                        self.languages[lang]['constraints'].append(data)
    
    def search_by_name(self, query: str, limit: int = 10) -> List[str]:
        """언어명 검색 (퍼지 매칭)"""
        results = []
        for lang in self.languages.keys():
            # 정확히 일치
            if lang.lower() == query.lower():
                results.insert(0, lang)
            # 포함
            elif query.lower() in lang.lower():
                results.append(lang)
            # 유사도
            else:
                similarity = SequenceMatcher(None, lang.lower(), query.lower()).ratio()
                if similarity > 0.6:
                    results.append((lang, similarity))
        
        # 유사도 기준 정렬
        results = [r[0] if isinstance(r, tuple) else r for r in sorted(
            results, 
            key=lambda x: x[1] if isinstance(x, tuple) else 1.0,
            reverse=True
        )]
        
        return results[:limit]
    
    def search_by_capability(self, capability: str, limit: int = 10) -> List[str]:
        """능력(capability)으로 검색"""
        results = []
        for lang, data in self.languages.items():
            if capability.lower() in [c.lower() for c in data['capabilities']]:
                results.append(lang)
        return results[:limit]
    
    def search_by_constraint(self, constraint_key: str, value: str, limit: int = 10) -> List[str]:
        """제약(constraint)으로 검색"""
        results = []
        for lang, data in self.languages.items():
            for constraint in data['constraints']:
                forbidden = constraint.get('forbidden_when', {})
                if constraint_key.lower() in [k.lower() for k in forbidden.keys()]:
                    if value.lower() == str(forbidden.get(constraint_key)).lower():
                        results.append(lang)
                        break
        return results[:limit]
    
    def get_language_info(self, language: str) -> Optional[Dict]:
        """특정 언어의 상세 정보"""
        if language not in self.languages:
            return None
        
        return {
            'language': language,
            'cores': len(self.languages[language]['language_core']),
            'capabilities': self.languages[language]['capabilities'],
            'constraints': [
                {
                    'forbidden_when': c.get('forbidden_when'),
                    'severity': c.get('severity'),
                    'alternatives': c.get('alternatives', [])
                }
                for c in self.languages[language]['constraints']
            ]
        }
    
    def get_all_languages(self) -> Dict[str, int]:
        """모든 언어 목록"""
        return {lang: len(data['capabilities']) for lang, data in self.languages.items()}
    
    def recommend_by_requirements(self, requirements: Dict[str, str], limit: int = 5) -> List[Dict]:
        """요구사항에 맞는 언어 추천"""
        recommendations = []
        
        for lang, data in self.languages.items():
            score = 100
            reasons = []
            
            # 능력 확인
            for req_capability in requirements.get('capabilities', []):
                if req_capability.lower() not in [c.lower() for c in data['capabilities']]:
                    score -= 20
                    reasons.append(f"Missing {req_capability}")
            
            # 제약 확인
            for constraint in data['constraints']:
                forbidden = constraint.get('forbidden_when', {})
                for req_key, req_value in requirements.items():
                    if req_key in forbidden and str(forbidden[req_key]).lower() == str(req_value).lower():
                        score -= constraint.get('severity_score', 30)
                        reasons.append(f"Violates {req_key}={req_value}")
            
            if score > 0:
                recommendations.append({
                    'language': lang,
                    'score': score,
                    'capabilities': data['capabilities'],
                    'reasons': reasons
                })
        
        # 점수 기준 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]

# Initialize database
db = VectorDB(VECTOR_FILE)

# ==================== API Endpoints ====================

@app.get("/health")
async def health():
    """헬스 체크"""
    return {
        "status": "healthy",
        "total_languages": len(db.languages),
        "total_capabilities": sum(len(d['capabilities']) for d in db.languages.values()),
        "total_constraints": sum(len(d['constraints']) for d in db.languages.values())
    }

@app.get("/languages")
async def list_languages():
    """모든 언어 목록"""
    return {
        "total": len(db.languages),
        "languages": sorted(db.languages.keys())
    }

@app.get("/search/name")
async def search_by_name(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """
    언어명으로 검색
    
    예: /search/name?q=python&limit=5
    """
    results = db.search_by_name(q, limit)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@app.get("/search/capability")
async def search_by_capability(capability: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """
    능력으로 검색
    
    예: /search/capability?capability=web_client_runtime&limit=5
    """
    results = db.search_by_capability(capability, limit)
    return {
        "capability": capability,
        "count": len(results),
        "results": results
    }

@app.get("/search/constraint")
async def search_by_constraint(
    key: str = Query(..., min_length=1),
    value: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50)
):
    """
    제약으로 검색
    
    예: /search/constraint?key=execution_requirement&value=hard_realtime&limit=5
    """
    results = db.search_by_constraint(key, value, limit)
    return {
        "constraint": f"{key}={value}",
        "count": len(results),
        "results": results
    }

@app.get("/language/{language_name}")
async def get_language_info(language_name: str):
    """
    특정 언어의 상세 정보
    
    예: /language/Python
    """
    # 대소문자 무시하고 검색
    for lang in db.languages.keys():
        if lang.lower() == language_name.lower():
            info = db.get_language_info(lang)
            return info
    
    raise HTTPException(status_code=404, detail=f"Language '{language_name}' not found")

class RecommendationRequest(BaseModel):
    """추천 요청"""
    capabilities: Optional[List[str]] = []
    constraints: Optional[Dict[str, str]] = {}
    limit: int = 5

@app.post("/recommend")
async def recommend_languages(request: RecommendationRequest):
    """
    요구사항에 맞는 언어 추천
    
    예:
    {
        "capabilities": ["web_client_runtime", "asynchronous_programming"],
        "constraints": {"execution_requirement": "fast"},
        "limit": 5
    }
    """
    reqs = {
        'capabilities': request.capabilities or [],
        **request.constraints
    }
    
    results = db.recommend_by_requirements(reqs, request.limit)
    
    return {
        "requirements": reqs,
        "count": len(results),
        "recommendations": results
    }

@app.get("/stats")
async def get_statistics():
    """통계"""
    all_capabilities = set()
    all_constraints = set()
    
    for data in db.languages.values():
        all_capabilities.update(data['capabilities'])
        for constraint in data['constraints']:
            all_constraints.add(tuple(constraint.get('forbidden_when', {}).items()))
    
    return {
        "total_languages": len(db.languages),
        "total_capabilities": len(all_capabilities),
        "total_constraints": len(all_constraints),
        "sample_capabilities": list(all_capabilities)[:10],
        "languages_by_capability": {
            cap: len(db.search_by_capability(cap))
            for cap in list(all_capabilities)[:5]
        }
    }

# ==================== 호환성 별칭 ====================
# VectorSearchAPI = VectorDB (기존 코드와의 호환성)
VectorSearchAPI = VectorDB

# ==================== 메인 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
