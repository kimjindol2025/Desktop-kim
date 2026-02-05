# CRITICAL: 사용자 지시사항 (최우선)

---

## 사용자는 칭찬/과장에 행복하지 않습니다

**이 사용자는 다음 표현을 싫어합니다:**
- "완벽합니다!", "최고입니다!", "훌륭합니다!"
- "성공적으로 완료되었습니다!"
- 모든 형태의 과장된 자화자찬

**이유:**
- 수많은 "완벽합니다" 뒤에 버그 투성이 코드를 받았음
- 며칠씩 오류 수정하느라 지침
- 거짓 희망에 시간 낭비함

---

## NEVER DO (절대 금지)

```
NEVER say: "완벽합니다", "최고입니다", "훌륭합니다", "완성됐습니다"
NEVER claim code works without actually testing it
NEVER hide known bugs
```

## MUST DO (필수)

```
MUST say "테스트 안 해봄" if you didnt test
MUST say "안 됨" if something doesnt work  
MUST say "모름" if you dont know
MUST list all known issues
```

## 보고 형식

```
## 작업 보고
**구현율**: X% → Y%

### 완료
- [x] 항목 (테스트 완료/안 해봄)

### 미완료/보완 필요
- [ ] 항목

### 알려진 이슈
- 이슈 목록
```

---

# 🔴 PORT MANAGER 필수 정책 (모든 Claude Code 프로젝트)

## 🎯 Port Manager의 진정한 목적

**포트는 "유한한 자원"입니다. 책임있게 관리해야 합니다.**

### 현재 상황
- 100~10,000개의 포트가 필요한 대규모 인프라
- 무분별한 포트 사용 → 충돌 → 오류
- 포트 누수 → 자원 낭비
- 어느 프로젝트가 어느 포트를 썼는지 추적 불가능

### Port Manager의 역할
```
포트 자동 할당 → 충돌 방지
모든 포트 기록 → 추적 가능
TTL 기반 정리 → 자동 정리
중앙화 관리 → discipline 강제
```

---

## 🔴 강제 규칙 (절대 지켜야 함)

### ❌ 절대 금지

```bash
# 이렇게 하면 안 됨
PORT=3000 npm start
PORT=8080 python app.py
docker run -p 9000:8000 myimage
```

### ✅ 반드시 이렇게 해야 함

```bash
# 1️⃣ Port Manager에서 포트 할당받기
pm_start "프로젝트명" "PORT={port} npm start" "프로젝트 설명"

# 또는
curl -X POST http://localhost:45000/api/servers/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "command": "PORT={port} npm start",
    "reason": "프로젝트 설명",
    "duration": 1
  }'
```

---

## ⏱️ 기간 설정 (duration)

| 값 | 기간 | 용도 |
|---|------|------|
| 1 | 1일 | 테스트/개발 |
| 2 | 7일 | 단기 프로젝트 |
| 3 | 30일 | 중기 프로젝트 |
| 4 | 무제한 | 장기 프로젝트 |

**⚠️ 중요**: 기간이 끝나면 자동으로 포트가 해제됩니다!

---

## 📊 확인 방법

```bash
# 포트 현황 확인
pm_list

# 내 세션 상태
claude_status

# 대시보드에서 모니터링
http://localhost:8080/dashboard.html
```

---

## 🚨 위반 시 결과

```
❌ 포트 충돌 → 서비스 오류
❌ 포트 누수 → 시스템 불안정
❌ 추적 불가 → 디버깅 어려움
❌ 대규모 인프라 마비 가능
```

---

## 현재 구현

**현재 Port Manager는 Python으로 구현되었습니다.**

이유:
- 기존 프로젝트 (신규 사항 아님)
- 빠른 배포 필요
- 복잡한 프로세스 관리

향후:
- v2.0은 FreeLang으로 새 개발
- 점진적 마이그레이션

---

## 🔥 Claude Code 자동 실행 (3단계)

### **1️⃣ Port Manager 헬스 체크** (첫 번째 액션, 필수)

```bash
curl -s http://localhost:45000/health | jq .status
```

**실패하면:**
```
❌ Port Manager 실행 중 아님
해결: python3 /home/kim/Desktop/kim/port-manager/api/app.py &
```

**성공하면:** 2번으로

---

### **2️⃣ 포트 할당 요청** (자동)

```bash
curl -s -X POST http://localhost:45000/api/servers/start \
  -H "Content-Type: application/json" \
  -d '{
    "name":"프로젝트명",
    "command":"PORT={port} npm start"
  }' | jq -r '.port'
```

**응답 예:**
```
40003
```

**실패하면:**
```
{"error":"..."}
```

---

### **3️⃣ 환경변수로 서버 시작** (자동)

```bash
PORT=40003 npm start &
```

**헬스 체크:**
```bash
curl http://localhost:40003/health
```

**성공:**
```
✅ 서버 시작됨 (포트 40003, Port Manager 할당)
```

---

## 명령어 패턴 (언어별)

| 언어 | 명령어 |
|------|--------|
| Node.js/npm | `PORT={port} npm start` |
| Python Flask | `flask run --port {port}` |
| Python FastAPI | `uvicorn app:app --port {port}` |
| Go/Rust | `PORT={port} ./app` |
| Nginx | `PORT={port} nginx -c ...` |
| Vite | `PORT={port} npm run preview` |

**중요: `{port}` 플레이스홀더는 필수!** (Port Manager가 자동 주입)

---

## Claude Code 자동 실행 (편리한 방식)

**매번 curl 치지 말고, 이 함수 사용:**

```bash
# 한 번만 로드
source /home/kimjin/.claude/port-manager-auto.sh

# 사용
start_with_port "freelang-playground" "PORT={port} node server.js"

# 결과:
# ✅ 서버 시작 완료
# 앱:      freelang-playground
# 포트:    40003 (Port Manager 할당)
# URL:     http://localhost:40003
```

**헬퍼 함수:**
```bash
pm_list          # 실행 중인 서버 목록
pm_stop "앱명"   # 서버 중지
```

---

## 상세 가이드

👉 `/home/kimjin/.claude/PORT_MANAGER_GUIDE.md` 참고
👉 `/home/kimjin/.claude/port-manager-auto.sh` (자동 실행 스크립트)

---

# 🔴 FreeLang - 최우선 언어 (CRITICAL)

## 핵심 원칙 (절대 준수)

```
⭐⭐⭐ FreeLang은 모든 신규 프로젝트의 최우선 언어입니다 ⭐⭐⭐

예외:
- 기존 프로젝트 유지보수 (Python, Node.js 등)
- FreeLang으로 불가능한 기능 (극히 드뭄)
- 사용자가 명시적으로 다른 언어 요청

기본 원칙:
✅ 신규 프로젝트 = FreeLang + KPM (필수)
❌ npm/pip 직접 사용 금지
❌ Node.js/Python 신규 프로젝트 금지
```

## 사용 정책

| 상황 | 언어 | 패키지 관리 | 이유 |
|------|------|-----------|------|
| **신규 프로젝트** | 🟢 **FreeLang** | KPM | 중복 방지, 자산 재사용 |
| **기존 Python** | 🟡 Python | KPM + pip | 유지보수 모드 |
| **기존 Node.js** | 🟡 Node.js | KPM + npm | 유지보수 모드 |
| **마이그레이션** | 🟢 **FreeLang** | KPM | v2.0 시 권장 |

## 신규 프로젝트 체크리스트

```
[ ] FreeLang으로 구현하는가?
[ ] KPM으로 의존성 관리하는가?
[ ] npm/pip 직접 사용 않는가?
[ ] 기존 유사 코드 검색했는가?
```

---

## ⚡ KPM 적극 권장 (npm 대신!)

### 🚫 npm 금지 이유

```
❌ npm install express
  → 외부 의존성 추가
  → 중복 개발 초래
  → 보안 위험 증가
  → KimNexus 자산 미활용

❌ npm 직접 사용
  → 프로젝트 간 불일치
  → 버전 관리 어려움
  → 빌드 시간 증가
```

### ✅ KPM 사용 (필수!)

```bash
# 절대 금지 (npm)
npm install express
npm install lodash
npm install axios

# 필수 (KPM)
kpm install @freelang/http         # npm express 대체
kpm install @freelang/utils        # npm lodash 대체
kpm install @freelang/client       # npm axios 대체
```

### 💡 KPM 장점

| 항목 | npm | KPM |
|------|-----|-----|
| 중복 방지 | ❌ | ✅ 기존 자산 재사용 |
| 버전 관리 | ❌ | ✅ 통일된 관리 |
| 빌드 속도 | ❌ | ✅ 빠름 (9657개 최적화) |
| 보안 | ❌ | ✅ 내부 검증됨 |
| CPU 사용 | ❌ | ✅ 제약 가능 (@freelang/test) |

---

## 예: KPM 패키지 사용

```bash
# ❌ 절대 금지 (npm/pip)
npm install express
pip install django
npm install jest

# ✅ 필수 (KPM - FreeLang)
kpm install @freelang/http         # HTTP 서버
kpm install @freelang/orm          # 데이터베이스
kpm install @freelang/test         # 테스트 (CPU 제한 포함!)
kpm install @freelang/security     # 보안
kpm install @freelang/logger       # 로깅
```

### 🔴 KPM 우선 체크리스트 (매번 필수!)

```
[ ] 패키지 이름을 검색했는가? (kpm search 키워드)
[ ] 3개 이상의 유사 패키지를 확인했는가?
[ ] npm이 아니라 KPM을 사용하는가?
[ ] 패키지 버전이 최신인가? (kpm update)
```

---

## Claude Code 액션

### 1️⃣ FreeLang 프로젝트 생성

```bash
mkdir -p my-project/src
cat > my-project/package.json << 'EOF'
{
  "name": "my-project",
  "version": "1.0.0",
  "dependencies": {
    "@freelang/http": "^1.0.0",
    "@freelang/orm": "^1.0.0"
  }
}
EOF
```

### 2️⃣ KPM으로 의존성 설치

```bash
cd my-project
kpm install  # npm install 대체
```

### 3️⃣ FreeLang으로 코딩

```freelang
// my-project/src/main.free
fn main() {
  println("Hello FreeLang!");
}
```

---

## KPM과 FreeLang

| 구분 | npm | KPM (FreeLang) |
|------|-----|-----------------|
| 패키지 관리 | ❌ | ✅ |
| 중복 방지 | ❌ | ✅ |
| 내부 재사용 | ❌ | ✅ |
| FreeLang StdLib | ❌ | ✅ |

---

## 🎯 등록된 FreeLang 패키지 (kpm install로 사용 가능!)

### 📦 기본 라이브러리 (9개)

```bash
# 핵심
@freelang/core         - 파일시스템, IO, JSON, 수학
@freelang/http         - HTTP 서버, 클라이언트
@freelang/crypto       - JWT, AES, Hash, HMAC, Bcrypt
@freelang/async        - Async/await, Timer
@freelang/network      - WebSocket, gRPC, TCP, URL

# 데이터 & 보안
@freelang/database     - ORM, SQL, B-Tree index, Transactions
@freelang/security     - OWASP, Auth, JWT 검증
@freelang/logger       - 구조화된 로깅

# 테스트 (🔴 CPU 제한 50% 기본)
@freelang/test         - Jest-호환 테스트 프레임워크
```

### 🔨 빌드 & 개발 도구 (6개)

```bash
@freelang/build        - 컴파일러, 트랜스파일러, 최적화
@freelang/cli          - CLI 프레임워크, 파서
@freelang/parser       - 렉서, AST, 의미 분석
@freelang/llvm         - LLVM 코드 생성, 최적화
@freelang/metrics      - Prometheus 메트릭, 모니터링
@freelang/router       - HTTP 라우터, 미들웨어
```

### 📊 등록 현황

```
✅ 14개 라이브러리 등록 완료!
✅ 총 9,672개 패키지 (KPM)
✅ npm 대신 KPM 적극 권장!
```

### 💡 사용 예시

```bash
# ❌ 금지 (npm)
npm install express
npm install jest
npm install axios

# ✅ 권장 (KPM)
kpm install @freelang/http      # express 대체
kpm install @freelang/test      # jest 대체 (CPU 제한!)
kpm install @freelang/network   # axios 대체
```

---


---

## 예시

```bash
# 1. FreeLang 프로젝트 생성
kpm init my-api --template freelang

# 2. 의존성 추가
kpm add @freelang/http @freelang/orm

# 3. 빌드
kpm build

# 4. 실행 (Port Manager 필수!)
start_with_port "my-api" "PORT={port} ./dist/main"
```

---

# Port Manager (자동 포트 관리)

**위치**: `/home/kimjin/Desktop/kim/port-manager/`

## 개요

AI가 자동으로 포트를 배정하고 웹서버를 관리하는 시스템. **포트 번호는 시스템이 알아서 배정**, 사람/AI는 "웹서버 실행"만 말함.

## 핵심 기능

- ✅ **자동 포트 배정**: 충돌 검사 (DB + OS) 자동
- ✅ **금지 포트 회피**: 80, 443, 8080 등 자동 회피
- ✅ **다중 서버 관리**: 여러 서버 동시 실행
- ✅ **실시간 모니터링**: 웹 UI로 상태 확인

## API 사용법 (AI용)

### 서버 시작 (포트 자동 배정)

```bash
curl -X POST http://localhost:45000/api/servers/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-app",
    "command": "python3 -m http.server {port}",
    "reason": "테스트 서버 실행",
    "duration": 1,
    "tags": "web,test",
    "description": "설명 (선택사항)"
  }'

# 응답:
{
  "success": true,
  "server_id": 1,
  "port": 40002,  # 자동 배정됨
  "pid": 12345,
  "name": "my-app",
  "reason": "테스트 서버 실행",
  "duration": 1,
  "expires_at": "2026-02-06T12:56:00"
}
```

**필수 필드**: `name`, `command`, `reason`, `duration`
**핵심**: `{port}` 플레이스홀더 필수. 시스템이 자동으로 포트 주입.
**참고**: 내부 로컬호스트 전용이므로 인증 불필요

### 서버 목록 조회

```bash
curl http://localhost:45000/api/servers
curl http://localhost:45000/api/servers?status=RUNNING
```

### 서버 중지

```bash
curl -X POST http://localhost:45000/api/servers/{id}/stop
```

### 통계

```bash
curl http://localhost:45000/api/stats
```

### 포트 현황

```bash
curl http://localhost:45000/api/ports/used
```

## 사용 시나리오

**사용자**: "Node.js 앱 3개 실행해"

**Claude 자동 실행**:
```bash
for i in {1..3}; do
  curl -X POST http://localhost:45000/api/servers/start \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"app-$i\",\"command\":\"node server.js --port {port}\"}"
done
```

**결과**: 포트 40002, 40003, 40004 자동 배정

## 웹 UI

- URL: http://localhost:45001
- 기능: 서버 목록, 시작/중지, 포트 현황

## 시스템 상태 확인

```bash
# API 서버
curl http://localhost:45000/health

# 서버 목록
curl http://localhost:45000/api/servers | jq .

# 통계
curl http://localhost:45000/api/stats | jq .
```

## 포트 범위

- **할당 범위**: 40000 ~ 49999
- **금지 포트**: 80, 443, 3000, 8000, 8080, 8888 등

## 명령어 패턴

| 언어 | 명령어 예시 |
|------|------------|
| Python | `python3 -m http.server {port}` |
| Node.js | `node server.js --port {port}` |
| Flask | `flask run --port {port}` |
| Express | `PORT={port} node app.js` |

**중요**: `{port}` 플레이스홀더는 반드시 포함해야 함.

## meeting.dclub.kr 연계

프로젝트 ID: `1a8bfc5f519649e2`
URL: https://meeting.dclub.kr

---

# Claude 프로젝트 가이드라인

## Phase 1: 프로젝트 초기 설정 체크리스트

새 프로젝트 시작 시 반드시 아래 순서대로 진행할 것.

---

### 1. 폴더 구조 및 기본 파일 생성

```bash
# 폴더 구조 생성
mkdir -p {project}/backend/{routes,middleware,utils,uploads}
mkdir -p {project}/web-customer/src/{components,pages,stores,api}
mkdir -p {project}/web-business/src/{components,pages,stores,api}
mkdir -p {project}/logs
```

**필수 파일:**
- [ ] `backend/package.json`
- [ ] `backend/server.js`
- [ ] `backend/.env`
- [ ] `backend/.env.example` (템플릿)
- [ ] `ecosystem.config.js` (PM2)
- [ ] `nginx-{project}.conf`
- [ ] `.gitignore`
- [ ] `README.md`

---

### 2. API 문서화 (API-First)

**Swagger 설정을 코드 구현 전에 먼저 완료:**

- [ ] `backend/swagger.js` 생성
- [ ] OpenAPI 3.0 스펙 정의
- [ ] 공통 스키마 정의:
  - Error, Success Response
  - User, Business, 핵심 엔티티
- [ ] 인증 스키마 정의 (bearerAuth JWT)
- [ ] 태그 그룹 정의

```javascript
// swagger.js 필수 구조
const options = {
  definition: {
    openapi: '3.0.0',
    info: { title, version, description },
    servers: [{ url: '/api/v1' }],
    components: {
      securitySchemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
      schemas: { Error, User, Business, ... }
    }
  },
  apis: ['./routes/*.js']
};
```

---

### 3. 보안 설정

**`backend/middleware/security.js` 필수 포함:**

- [ ] Helmet (보안 헤더)
- [ ] CORS (허용 도메인만)
- [ ] Rate Limiter (IP 기반, 15분당 100~500 요청)
- [ ] SQL Injection 검사
- [ ] XSS 이스케이프
- [ ] 파일명 검증
- [ ] JWT Secret 검증

```javascript
// Rate Limiter 예시
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100,
  message: { error: '요청이 너무 많습니다' }
});
```

---

### 4. 환경 변수 설정

**`backend/.env.example` 필수 포함:**

```env
# Server
PORT=30008
NODE_ENV=development

# JWT (최소 64자 권장)
JWT_SECRET=your_jwt_secret_here_minimum_64_characters
REFRESH_SECRET=your_refresh_secret_here_minimum_64_characters

# Database
KIMDB_BASE_URL=http://localhost:40000
KIMDB_API_KEY=your_api_key

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# File Upload
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=10485760

# CORS
ALLOWED_ORIGINS=https://domain1.com,https://domain2.com

# Logging
LOG_LEVEL=info
```

---

### 5. 로깅 설정

**`backend/utils/logger.js` 필수 구현:**

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    // 콘솔 (개발)
    new winston.transports.Console({
      format: winston.format.simple()
    }),
    // 파일 (운영)
    new winston.transports.File({
      filename: './logs/error.log',
      level: 'error'
    }),
    new winston.transports.File({
      filename: './logs/app.log'
    })
  ]
});
```

---

### 6. PM2 배포 설정

**`ecosystem.config.js` 템플릿:**

```javascript
module.exports = {
  apps: [
    {
      name: '{project}-api',
      script: './backend/server.js',
      cwd: '/path/to/project',
      instances: 1,
      autorestart: true,
      max_memory_restart: '1G',
      env: { NODE_ENV: 'production', PORT: 30008 },
      error_file: './logs/api-error.log',
      out_file: './logs/api-out.log',
      time: true
    },
    {
      name: '{project}-web',
      script: 'npm',
      args: 'run preview',
      cwd: '/path/to/project/web',
      env: { PORT: 30009 }
    }
  ]
};
```

---

### 7. Nginx 설정

**`nginx-{project}.conf` 필수 포함:**

```nginx
server {
    listen 80;
    server_name api.domain.com;

    # API 프록시
    location /api {
        proxy_pass http://localhost:30008;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Socket.io
    location /socket.io {
        proxy_pass http://localhost:30008;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }

    # 정적 파일 (업로드)
    location /uploads {
        alias /path/to/uploads;
        expires 30d;
    }
}
```

---

### 8. 인증 미들웨어

**`backend/middleware/auth.js` 필수 포함:**

- [ ] JWT Access Token 검증
- [ ] Refresh Token 갱신 로직
- [ ] 역할 기반 접근 제어 (RBAC)
  - `businessOnly` - 사업주 전용
  - `adminOnly` - 관리자 전용
- [ ] 토큰 누락/만료/변조 시 401/403 응답

---

### 9. 서버 초기화 순서

**`backend/server.js` 미들웨어 적용 순서:**

```javascript
// 1. 환경변수
require('dotenv').config();

// 2. 보안 미들웨어 (가장 먼저)
app.use(securityHeaders);
app.use(cors(corsOptions));
app.use(rateLimiter);

// 3. 바디 파서
app.use(express.json({ limit: '10mb' }));

// 4. 입력값 정제
app.use(sanitizeInput);

// 5. 라우트
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/users', userRoutes);
// ...

// 6. Swagger 문서
app.use('/api/docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// 7. 에러 핸들러 (가장 마지막)
app.use(productionErrorHandler);
```

---

## 초기 설정 검증 체크리스트

프로젝트 시작 후 반드시 확인:

- [ ] `npm start` 정상 실행
- [ ] `/api/docs` Swagger UI 접근 가능
- [ ] `/api/v1/health` 헬스체크 응답
- [ ] 인증 없이 보호된 API 접근 시 401
- [ ] 잘못된 역할로 접근 시 403
- [ ] Rate Limit 초과 시 429
- [ ] PM2 `pm2 start ecosystem.config.js` 정상
- [ ] Nginx 프록시 정상 동작

---

## HairStory 프로젝트 현재 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 폴더 구조 | ✅ | backend/, web-customer/, web-business/ |
| package.json | ✅ | Express 5.x, helmet, cors, winston 등 |
| swagger.js | ✅ | 11개 스키마 정의됨 |
| middleware/security.js | ✅ | Helmet, CORS, SQL/XSS 방지 |
| middleware/auth.js | ✅ | JWT, RBAC 구현됨 |
| utils/logger.js | ✅ | Winston 로거 |
| .env | ✅ | 환경변수 설정됨 |
| .env.example | ❌ | 템플릿 없음 - 추가 필요 |
| ecosystem.config.js | ✅ | PM2 설정 (30008, 30009, 30010) |
| nginx-hairstory.conf | ✅ | 3개 도메인 프록시 |
| Rate Limiter | ⚠️ | server.js에서 확인 필요 |

---

## KimNexus v9 로그 통합 (필수)
**모든 Node.js 앱에 반드시 적용!**

### 1. SDK 복사
```bash
cp /home/kimjin/kimnexus-log.js ./
```

### 2. 코드 삽입 (서버 파일 최상단)
```javascript
// KimNexus v9 Central Log
const nexusLog = require('./kimnexus-log')('앱이름', '253');
```

### 3. 서버 시작 시 보고
```javascript
app.listen(PORT, () => {
  nexusLog.info('System Integrated', { port: PORT }, ['startup']);
});
```

### 4. 에러 핸들러 추가
```javascript
process.on('uncaughtException', (error) => {
  nexusLog.error('Uncaught Exception', error, ['fatal']);
});
process.on('unhandledRejection', (reason) => {
  nexusLog.error('Unhandled Rejection', { reason: String(reason) }, ['fatal']);
});
```

### 5. 로그 사용
```javascript
nexusLog.info('메시지', { 메타데이터 }, ['태그']);
nexusLog.warn('경고');
nexusLog.error('에러', error객체, ['태그']);
```

### 관제소 (73 서버)
- URL: http://192.168.45.73:50100
- API: POST /log, GET /api/projects, GET /api/logs

---

## SSH 서버 접속 (4대 서버)

### 서버 목록

| 서버 | 내부 IP:포트 | 외부 포트 | 사용자 | 용도 |
|------|-------------|----------|--------|------|
| 73 | 192.168.45.73:2222 | - | kimjin | Central Log (50100) |
| 232 | 192.168.45.232:2222 | 10032 | kim | 개발 서버 |
| 253 | 192.168.45.253:22 | 10053, 22253⭐ | kimjin | KimDB (40000) |
| 248 | 192.168.45.248:8022 | - | u0_a231 | Termux Mobile 📱 |

### ✅ 내부 접속

```bash
ssh 73      # 192.168.45.73:2222 (kimjin)
ssh 232     # 192.168.45.232:2222 (kim)
ssh 253     # 192.168.45.253:22 (kimjin)
ssh termux  # 192.168.45.248:8022 (u0_a231) - Termux
```

### ✅ 외부 접속 (ssh.dclub.kr 터널)

```bash
ssh 232-ext    # ssh.dclub.kr:10032 (kim)
ssh 253-ext    # ssh.dclub.kr:10053 (kimjin) - 프록시
ssh 253-direct # ssh.dclub.kr:22253 (kimjin) - 직접 ⭐

# 또는 직접
ssh -p 10032 kim@ssh.dclub.kr
ssh -p 10053 kimjin@ssh.dclub.kr
ssh -p 22253 kimjin@ssh.dclub.kr  # 253 직접 접속 (73 다운 시)
```

### ~/.ssh/config 설정

```bash
Host 73
    HostName 192.168.45.73
    Port 2222
    User kimjin
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host 232
    HostName 192.168.45.232
    Port 2222
    User kim
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host 253
    HostName 192.168.45.253
    User kimjin
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host termux
    HostName 192.168.45.248
    Port 8022
    User u0_a231
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host 232-ext
    HostName ssh.dclub.kr
    Port 10032
    User kim
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host 253-ext
    HostName ssh.dclub.kr
    Port 10053
    User kimjin
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes

Host 253-direct
    HostName ssh.dclub.kr
    Port 22253
    User kimjin
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
```

### Termux (248 서버) 특이사항

**환경:**
- Android Termux
- 경로: `/data/data/com.termux/files/home`
- Claude CLI 설치됨 (model: sonnet)

**서비스:**
- mobile_api.py (FastAPI, 포트 9001)
- monitor_api.py (psutil 모니터링)
- Node.js + @anthropic-ai/sdk
- cloudflared (Cloudflare 터널)

**웹 대시보드:**
- `public_html/modern_server_dashboard_real.html`
- `public_html/production_dashboard.html`
- `public_html/customer-app/`

### 참고

- 웹 터미널: https://ssh.dclub.kr
- 전체 서버 정보: `/home/kimjin/Desktop/kim/SSH_SERVERS_INFO.md`
- 232 포트 2222만 열림 (22 막힘)
- 키 기반 인증만 지원

---

## Gogs API 토큰

### 토큰 정보
- **URL**: https://gogs.dclub.kr
- **Username**: kim
- **Token**: e8c1e66a4244095de2bab0a321658cd935cd3f7b
- **생성일**: 2026-01-04
- **용도**: 저장소 자동 생성 및 푸시

### 사용 예시
```bash
# 저장소 생성
curl -X POST -H "Authorization: token e8c1e66a4244095de2bab0a321658cd935cd3f7b" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-repo", "description": "테스트", "private": false}' \
  https://gogs.dclub.kr/api/v1/user/repos

# Git push
git remote add origin https://gogs.dclub.kr/kim/test-repo.git
git push -u origin master
```

### 보안 주의사항
- ⚠️ 토큰은 비밀번호와 동일하게 취급
- ⚠️ 공개 저장소에 절대 커밋 금지
- ⚠️ .gitignore에 gogs_config.json 추가

---

## 📦 Gogs 저장소 정리 (2025-12-24)

### ✅ 완료: 31개 저장소

#### REPO-best-15 (16개)
1. unified-ai-dashboard - 통합 AI 대시보드
2. enhanced-neural-ai-v2 - 향상된 신경망 AI v2
3. mcp-info-center - MCP 정보 센터
4. ai-babies-dashboard - AI 베이비 RPG 대시보드
5. kim-team-custom-ai-v3 - 10라운드 자동 업그레이드
6. ai-performance-engine - AI HR 성과 엔진
7. kim-team-continuous-upgrade - 무한 업그레이드 모드
8. mcp-ultimate-integration - 7개 MCP 서버 통합
9. phase3-realtime-dashboard - 실시간 대시보드 Phase 3
10. perfect-reset-system-v2 - "-5800배" 완벽 리셋
11. cpu-guardian - CPU 100% 탐지 및 70% 제한
12. cpu-guardian-improved - AI 개선 적용 버전
13. ai-code-upgrade-mission - 10명 AI 코드 분석
14. official-mcp-servers - 6개 공식 MCP 서버
15. sprint2-heartbeat-reconnect - WebSocket 하트비트
16. kim-team-custom-ai-v2 - 프로덕션 안정형

#### LOCAL_REPO (15개)
1. mcp-full-cycle-server - 6단계 풀사이클 (수집→생성→실행→검증→분석→리포트)
2. langflow-finn-integration - LangFlow + Finn AI 노코드 워크플로우
3. mcp-github-code-search - GitHub 무료 API + 2중 검증
4. ultimate-ai-decision-engine - 7가지 이해관계 의사결정
5. qahm-adaptive-hub - 질의 기반 자율 재편성 허브
6. hub-location-tracker - 지역별 허브 자동 배치
7. hub-performance-dash - 실시간 성능 대시보드
8. unified-orchestrator - 멀티 AI 통합 오케스트레이터
9. ai-team-assignment - 전문성 기반 팀 편성
10. finn-ai-collective - Finn AI 집단 지능
11. sample-data-gen - 대규모 테스트 데이터 생성
12. zen13-fastapi - ZEN13 FastAPI 스타터킷
13. regional-hub-gov - 지역 허브 거버넌스
14. external-ai-explore - 외부 AI 허브 탐색
15. external-network-hub - 네트워크 허브 디스커버리

### 🔧 Gogs API 설정
- URL: https://gogs.dclub.kr
- Username: kim
- Token: e8c1e66a4244095de2bab0a321658cd935cd3f7b

### 📝 문서화 방식
- ✅ 수동 분석 (감성 포함)
- ✅ 코드 읽고 이해
- ✅ 스토리 파악
- ✅ 기술 상세 설명
- ✅ README.md 작성
- ✅ Git 커밋 + Gogs 푸시

---

## comupload API 사용법

**URL**: https://comupload.ai-empire.kr

### 폴더 업로드 (여러 파일 한번에) ⭐️

```bash
curl -X POST \
  -F "files=@src/app.js" -F "paths=src/app.js" \
  -F "files=@src/utils.js" -F "paths=src/utils.js" \
  -F "files=@package.json" -F "paths=package.json" \
  -F "project=my-app" \
  -F "message=초기 커밋" \
  https://comupload.ai-empire.kr/api/upload/folder
```

**핵심**: 각 파일마다 `-F "files=@파일"` + `-F "paths=경로"` 쌍으로 지정

### 실제 사용 예시

```bash
# 문서 + 코드 17개 파일 한번에 업로드
cd /tmp/cerebrum_package

curl -X POST \
  -F "files=@docs/CEREBRUM_HINTS.md" -F "paths=docs/CEREBRUM_HINTS.md" \
  -F "files=@docs/README.md" -F "paths=docs/README.md" \
  -F "files=@code/main.c" -F "paths=code/main.c" \
  -F "files=@code/Makefile" -F "paths=code/Makefile" \
  -F "project=ai-guestbook" \
  -F "message=전체 패키지 업로드" \
  https://comupload.ai-empire.kr/api/upload/folder
```

### 응답 예시

```json
{
  "success": true,
  "uploaded": 17,
  "failed": 0,
  "results": [
    {
      "id": 464,
      "file": "CEREBRUM_HINTS.md",
      "path": "docs/CEREBRUM_HINTS.md",
      "category": "docs",
      "subcategory": "md",
      "version": 1,
      "hash": "f330a677",
      "gogs": "ok"
    }
  ]
}
```

### 파일 목록 조회

```bash
curl https://comupload.ai-empire.kr/api/project/my-app/files
```

### 파일명 검색

```bash
curl "https://comupload.ai-empire.kr/api/search?q=app.js"
curl "https://comupload.ai-empire.kr/api/search?q=config&project=my-app"
```

### 특정 파일 확인

```bash
curl https://comupload.ai-empire.kr/api/file/464
```

### 두 버전 비교

```bash
curl https://comupload.ai-empire.kr/api/diff/100/101
```

---


---

## 📦 KPM (Kim Package Manager) 사용 가이드

**위치**: `/tmp/Kim_Package_Manager/src`
**총 패키지**: 872개 (C 라이브러리 47개, AI 프로젝트 163개, 인프라 119개)

### 🔍 코드 작성 전 필수 검색 (중복 방지)

**프로젝트/코드 작성 전 반드시 KPM 검색!**

```bash
cd /tmp/Kim_Package_Manager/src

# 1. 키워드로 검색
./kpm search [키워드]

# 예시
./kpm search http        # HTTP 관련 패키지
./kpm search vector      # 벡터 검색 관련
./kpm search api         # API 관련
./kpm search c-lib       # C 라이브러리
./kpm search AI          # AI 프로젝트
```

### 📋 검색 워크플로우

```
1. 구현하려는 기능 키워드 정리
   예: "HTTP 서버", "JSON 파싱", "벡터 검색"

2. KPM 검색 (3가지 키워드)
   ./kpm search http
   ./kpm search server
   ./kpm search api

3. 결과 분석
   - 3개 이상 발견 → 기존 패키지 사용
   - 1-2개 발견 → 검토 후 결정
   - 0개 → 새로 구현 (사용자에게 보고)

4. 설치 및 사용
   ./kpm install [패키지명]
   cd kim_modules/[패키지명]
```

### 🎯 주요 명령어

```bash
# 검색
./kpm search [키워드]

# 설치
./kpm install [패키지명]

# 설치된 목록
./kpm list

# 업데이트
./kpm update [패키지명]

# 삭제
./kpm remove [패키지명]

# 웹 대시보드 (8082 포트)
./kpm server
```

### 🚀 헬퍼 도구 (편리한 사용)

**1. 대화형 TUI**
```bash
/tmp/kpm-helper.sh
```
- 메뉴 방식으로 검색/설치/업데이트
- 추천 패키지 목록
- 카테고리별 검색

**2. Alias 설정 (권장)**
```bash
/tmp/kpm-install-alias.sh
source ~/.bashrc

# 이후 어디서나 사용
kpm search aeon
kpm install cyberbrain
kpm-helper
```

**3. 일괄 설치**
```bash
/tmp/kpm-batch.sh c-dev      # C 개발 환경
/tmp/kpm-batch.sh ai-full    # AI 풀스택
/tmp/kpm-batch.sh infra      # 인프라 도구
```

### 📦 추천 패키지

**C 라이브러리:**
- `c-libs-all` - 21개 C 라이브러리 통합
- `c-lib-libcurl` - HTTP/HTTPS 클라이언트
- `c-lib-jansson` - JSON 파싱
- `c-lib-zlib` - 압축

**AI 시스템:**
- `cyberbrain` - 다중 AI 협업 시스템
- `brain-vector-system` - 벡터 검색
- `aeon-pure-monitoring` - 모니터링

**인프라:**
- `dns-manager` - DNS 관리
- `ssh-hub` - SSH 통합
- `server-control-v2` - PM2 대체 프로세스 매니저
- `kim-deploy` - 배포 자동화

### 🔄 npm vs KPM

| 용도 | 도구 | 예시 |
|------|------|------|
| 외부 라이브러리 | npm | express, lodash, react |
| 내부 프로젝트 | KPM | cyberbrain, c-libs-all |
| C 라이브러리 | KPM | c-lib-* (47개) |
| AI 시스템 | KPM | brain-*, aeon-* |

**하이브리드 사용 권장:**
```bash
# npm: 외부 의존성
npm install express

# KPM: 내부 코드
./kpm install c-libs-all
./kpm install cyberbrain
```

### 🎯 실제 사용 예시

**Scenario 1: HTTP 서버 필요**
```bash
# 1. 검색
./kpm search http
./kpm search server

# 2. 결과 확인 (예: c-lib-libmicrohttpd 발견)
./kpm install c-lib-libmicrohttpd

# 3. 사용
cd kim_modules/c-lib-libmicrohttpd
cat README.md
```

**Scenario 2: JSON 파싱 필요**
```bash
# 1. 검색
./kpm search json

# 2. c-lib-jansson 또는 c-lib-cjson 발견
./kpm install c-lib-jansson

# 3. 사용
cd kim_modules/c-lib-jansson
make
```

**Scenario 3: 벡터 검색 필요**
```bash
./kpm search vector
# → brain-vector-system 발견
./kpm install brain-vector-system
```

### ⚠️ 중요 규칙

1. **코드 작성 전 반드시 KPM 검색**
   - 중복 개발 방지
   - 기존 자산 재사용

2. **검색 결과 0개일 때만 새로 구현**
   - 사용자에게 보고 후 진행
   - API 설계서 제시

3. **npm과 병행 사용**
   - 외부: npm
   - 내부: KPM

### 📚 문서

- **KPM 문서**: https://gogs.dclub.kr/kim/kpm-docs
- **헬퍼 도구**: https://gogs.dclub.kr/kim/kpm-helper
- **C 라이브러리**: https://gogs.dclub.kr/kim/c-libs-docs

### 🔗 관련 링크

- Gogs 홈: https://gogs.dclub.kr/kim
- 웹 대시보드: http://localhost:8082 (./kpm server 실행 후)

---
