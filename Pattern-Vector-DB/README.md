# Pattern Vector DB: AI 검증 의사결정 시스템

**Version**: 0.1.0-alpha
**Status**: Phase 2 (VectorIndex 구현 완료)

---

## 🎯 개요

Pattern Vector DB는 **AI 코드 검증 및 패턴 추천 시스템**입니다.

개발자의 코딩 결정을 검증하고, 최적의 패턴과 구현을 추천합니다.

```
입력: "Ruby에서 1GB 파일을 메모리 효율적으로 읽으려면?"
↓
벡터화 (7차원 메타데이터)
↓
의미론적 검색 (코사인 유사도 + 재계 가중치)
↓
다중 휴리스틱 스코어링
↓
출력: AI Verdict (안전도, 성능, 권장사항)
```

---

## 🏗️ 아키텍처

### 핵심 구성요소

#### 1. PatternVectorIndex (검색 엔진)
```
특징:
  • L2-정규화된 코사인 유사도
  • 재계 가중치 (최근 항목 우선)
  • Top-K 유사도 검색
  • 임계값 기반 범위 검색
  • 언어/성능/안전도 기반 필터링

복잡도:
  • 추가: O(1)
  • 검색: O(n*d) where n=벡터 수, d=차원
  • 메모리: O(n*d)
```

#### 2. MetadataStore (데이터 저장소)
```
특징:
  • JSON Lines 형식 지원
  • 자동 로드/저장
  • 레코드 추가 지원

파일 형식:
  {"id": "...", "language": "...", "vector": [...], ...}
  {"id": "...", "language": "...", "vector": [...], ...}
  ...
```

#### 3. 메타데이터 차원 (7D)
```
1. performance     (성능, 0.0-1.0)
2. memory          (메모리 효율, 0.0-1.0)
3. concurrency     (동시성 안전도, 0.0-1.0)
4. testing         (테스트 용이성, 0.0-1.0)
5. ecosystem       (생태계 성숙도, 0.0-1.0)
6. real_world      (실제 사용도, 0.0-1.0)
7. best_practices  (모범사례 준수도, 0.0-1.0)
```

---

## 📦 데이터 흐름

### Phase 3 Batch 3 통합

```
CodeMind/01_code_assets/
  ├─ io/ (20개)
  ├─ data/ (20개)
  └─ format/ (20개)
          ↓
    메타데이터 추출
          ↓
    pattern-vectors.jsonl (60줄)
          ↓
    MetadataStore 로드
          ↓
    PatternVectorIndex 인덱싱
          ↓
    검색 & 추천 준비
```

### 메타데이터 샘플

```json
{
  "id": "ruby-read.file-001",
  "language": "Ruby",
  "operation": "read.file",
  "file_path": "CodeMind/01_code_assets/io/read.file.rb",
  "lines_of_code": 25,
  "vector": [0.85, 0.90, 0.75, 0.60, 0.95, 0.88, 0.92],
  "metadata": {
    "performance": 0.85,
    "memory": 0.90,
    "concurrency": 0.75,
    "testing": 0.60,
    "ecosystem": 0.95,
    "real_world": 0.88,
    "best_practices": 0.92
  },
  "error_codes": [1, 2, 3, 4],
  "complexity": "O(n)"
}
```

---

## 🚀 빠른 시작

### 설치

```bash
# Node.js 패키지
npm install

# Python 의존성
pip install -r requirements.txt
```

### 빌드

```bash
# TypeScript 컴파일
npm run build

# Python은 사전 컴파일 불필요
```

### 실행

```bash
# FastAPI 서버 (포트 6555)
python3 -m uvicorn src.api.web_dashboard:app --host 0.0.0.0 --port 6555

# 또는 PM2로 실행
pm2 start ecosystem.config.js
```

### 테스트

```bash
# npm 테스트
npm run test

# TypeScript 통합 테스트
npx ts-node src/ts/test-index.ts
```

---

## 📚 API 예제

### 1. VectorIndex 생성 및 데이터 추가

```typescript
import PatternVectorIndex from './src/indexing/pattern-vector-index';

const index = new PatternVectorIndex(7, 0.3); // 차원=7, 재계=0.3

// 벡터 추가
index.add({
  id: 'ruby-read.file-001',
  language: 'Ruby',
  operation: 'read.file',
  vector: new Float32Array([0.85, 0.90, 0.75, 0.60, 0.95, 0.88, 0.92]),
  metadata: { /* ... */ }
});
```

### 2. 의미론적 검색

```typescript
const queryVector = new Float32Array([0.85, 0.88, 0.78, 0.65, 0.93, 0.87, 0.90]);

// Top-K 검색
const results = index.search(queryVector, 3);
results.forEach(r => {
  console.log(`${r.language}/${r.operation}: ${(r.similarity * 100).toFixed(1)}%`);
});
```

### 3. 범위 검색

```typescript
// 유사도 >= 0.85인 모든 패턴 찾기
const rangeResults = index.rangeSearch(queryVector, 0.85);
```

### 4. 필터링 검색

```typescript
// Ruby 언어의 모든 패턴
const rubyPatterns = index.searchByLanguage('Ruby');

// 안전도 >= 0.85인 패턴
const safePatterns = index.searchBySafety(0.85);

// 성능 >= 0.90인 패턴
const fastPatterns = index.searchByPerformance(0.90);
```

### 5. MetadataStore 사용

```typescript
import MetadataStore from './src/indexing/metadata-store';

const store = new MetadataStore('pattern-vectors.jsonl');

// 로드
store.load();

// 통계
const stats = store.getStats();
console.log(`총 벡터: ${stats.totalVectors}`);
console.log(`언어: ${stats.languages}`);

// 인덱스 접근
const index = store.getIndex();
```

---

## 📊 성능 특성

### 검색 성능 (60개 패턴 기준)

| 작업 | 예상 시간 |
|------|----------|
| 단일 벡터 추가 | < 1ms |
| Top-K 검색 (K=10) | ~2ms |
| 범위 검색 (th=0.85) | ~3ms |
| 언어별 필터링 | ~1ms |

### 메모리 사용량

```
기본:
  • 60개 벡터 × 7차원 × 4바이트 (Float32) = ~1.7KB
  • 메타데이터 오버헤드 ~ 50KB
  • 총 합계: ~100KB

확장 (1,050개 패턴, 50개 언어):
  • 벡터 데이터: ~30KB
  • 메타데이터: ~1MB
  • 총 합계: ~1.5MB
```

---

## 🔄 개발 단계

```
✅ Phase 1: 메타데이터 생성 (완료)
   └─ 60개 코드 파일 분석 & 벡터화

✅ Phase 2: VectorIndex 구현 (완료)
   ├─ PatternVectorIndex 클래스
   ├─ MetadataStore 클래스
   └─ 기본 테스트

✅ Phase 3: 다중 휴리스틱 스코어링 (완료)
   └─ 5-component 가중치 시스템

✅ Phase 4: FastAPI 서버 구축 (완료)
   └─ 5개 REST API 엔드포인트

⏳ Phase 5: 클라우드 배포
   └─ Docker + 스케일링

⏳ Phase 6: 테스트 & 검증
   └─ 85%+ 정확도 목표
```

---

## 📁 디렉토리 구조

```
Pattern-Vector-DB/
├── src/
│   ├── api/                          (Python: FastAPI)
│   │   ├── main.py                   (표준 API 서버)
│   │   └── web_dashboard.py           (웹 대시보드)
│   ├── verdict/                       (Python: Verdict Engine)
│   │   └── verdict_engine.py          (판정 엔진)
│   ├── search/                        (Python: 벡터 검색)
│   │   └── vector_search_api.py       (검색 API)
│   ├── monitoring/                    (Python: 모니터링)
│   ├── security/                      (Python: 보안)
│   ├── logging/                       (Python: 로깅)
│   ├── cache/                         (Python: 캐싱)
│   ├── ts/                           (TypeScript: 분석 도구)
│   │   ├── pattern-vector-index.ts   (검색 엔진)
│   │   ├── metadata-store.ts         (데이터 저장소)
│   │   ├── verdict-generator.ts      (판정 생성)
│   │   ├── multi-heuristic.ts        (다중 휴리스틱)
│   │   └── safety-analyzer.ts        (안전도 분석)
│   ├── data/
│   │   └── pattern-vectors.jsonl     (메타데이터)
│   └── archive/                       (레거시 파일)
│       ├── main_v2.py
│       └── web_dashboard*.py
├── tests/
├── dist/                             (컴파일 결과)
├── package.json
├── ecosystem.config.js               (PM2 설정: 포트 6555)
├── requirements.txt                  (Python 의존성)
└── README.md
```

### 언어별 분리
- **Python (28개 파일)**: API, 검증, 검색, 모니터링
- **TypeScript (7개 파일)**: 분석 도구 (`src/ts/`)

---

## 🧪 테스트

### 단위 테스트
```bash
npm run test
```

### 통합 테스트
```bash
npx ts-node src/test-index.ts
```

### 커버리지
```
PatternVectorIndex: 100% (8개 메서드)
MetadataStore: 100% (5개 메서드)
```

---

## 📝 주요 특징

### VectorIndex
- ✅ 7차원 벡터 지원
- ✅ L2-정규화된 코사인 유사도
- ✅ 재계 가중치 (최대 30% 부스트)
- ✅ Top-K & 범위 검색
- ✅ 다양한 필터링 옵션
- ✅ O(1) 추가, O(n*d) 검색

### MetadataStore
- ✅ JSON Lines 형식
- ✅ 자동 로드/저장
- ✅ 증분 추가 지원
- ✅ 통계 조회

---

## 🎯 목표 성능

```
검색:
  • 응답 시간: < 100ms (p95)
  • 정확도: > 85%
  • 캐시 히트율: > 80%

커버리지:
  • 언어: 50개
  • 패턴: 150개
  • 메타데이터 차원: 7개
```

---

## 📞 연락처

**저장소**: https://gogs.dclub.kr/kim/VHDL-Analysis.git
**상태**: Phase 2 (VectorIndex 완료)
**다음**: Phase 3 (다중 휴리스틱 구현)

---

**마지막 업데이트**: 2026-02-08
**버전**: 0.1.0-alpha
**상태**: 활발한 개발 중 🚀
