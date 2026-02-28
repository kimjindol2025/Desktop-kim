"""
벡터 DB 검색 라이브러리
FastAPI 없이 순수 Python으로 구현
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

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
                results.insert(0, (lang, 1.0))
                continue
            
            # 포함
            if query.lower() in lang.lower():
                results.append((lang, 0.9))
                continue
            
            # 유사도
            similarity = SequenceMatcher(None, lang.lower(), query.lower()).ratio()
            if similarity > 0.6:
                results.append((lang, similarity))
        
        # 유사도 기준 정렬
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]
    
    def search_by_capability(self, capability: str, limit: int = 10) -> List[str]:
        """능력(capability)으로 검색"""
        results = []
        cap_lower = capability.lower()
        
        for lang, data in self.languages.items():
            for cap in data['capabilities']:
                if cap_lower in cap.lower() or cap.lower() == cap_lower:
                    results.append(lang)
                    break
        
        return results[:limit]
    
    def search_by_constraint(self, constraint_key: str, value: str, limit: int = 10) -> List[str]:
        """제약(constraint)으로 검색"""
        results = []
        key_lower = constraint_key.lower()
        value_lower = str(value).lower()
        
        for lang, data in self.languages.items():
            for constraint in data['constraints']:
                forbidden = constraint.get('forbidden_when', {})
                for fkey, fval in forbidden.items():
                    if fkey.lower() == key_lower and str(fval).lower() == value_lower:
                        results.append(lang)
                        break
        
        return results[:limit]
    
    def get_language_info(self, language: str) -> Optional[Dict]:
        """특정 언어의 상세 정보"""
        # 대소문자 무시 검색
        actual_lang = None
        for lang in self.languages.keys():
            if lang.lower() == language.lower():
                actual_lang = lang
                break
        
        if not actual_lang:
            return None
        
        data = self.languages[actual_lang]
        return {
            'language': actual_lang,
            'vector_count': len(data['language_core']),
            'capabilities': data['capabilities'],
            'constraints': [
                {
                    'forbidden_when': c.get('forbidden_when'),
                    'reason': c.get('reason', []),
                    'severity': c.get('severity'),
                    'alternatives': c.get('alternatives', [])
                }
                for c in data['constraints']
            ]
        }
    
    def get_all_languages(self) -> Dict[str, int]:
        """모든 언어 목록"""
        return {lang: len(data['capabilities']) for lang, data in self.languages.items()}
    
    def recommend_by_requirements(self, capabilities: List[str] = None, limit: int = 5) -> List[Dict]:
        """능력 기반 추천"""
        if not capabilities:
            capabilities = []
        
        recommendations = []
        cap_lower = [c.lower() for c in capabilities]
        
        for lang, data in self.languages.items():
            score = 0
            matched = 0
            
            for req_cap in cap_lower:
                for lang_cap in data['capabilities']:
                    if req_cap in lang_cap.lower():
                        score += 1
                        matched += 1
                        break
            
            if matched > 0 or len(cap_lower) == 0:
                recommendations.append({
                    'language': lang,
                    'score': matched,
                    'matched_capabilities': matched,
                    'total_capabilities': len(data['capabilities']),
                    'capabilities': data['capabilities'][:3]  # 처음 3개만
                })
        
        # 점수 기준 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def get_statistics(self) -> Dict:
        """통계"""
        all_capabilities = set()
        constraint_count = 0
        
        for data in self.languages.values():
            all_capabilities.update(data['capabilities'])
            constraint_count += len(data['constraints'])
        
        return {
            'total_languages': len(self.languages),
            'total_capabilities': len(all_capabilities),
            'total_constraints': constraint_count,
            'avg_capabilities_per_language': len(all_capabilities) / len(self.languages) if self.languages else 0,
            'languages': sorted(self.languages.keys())
        }

# 그래프 검색 (벡터 유사도)
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """코사인 유사도 계산"""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

