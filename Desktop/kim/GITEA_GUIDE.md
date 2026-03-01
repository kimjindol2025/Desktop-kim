# Gitea 설치 & 운영 가이드

**설치일**: 2026-03-01
**버전**: v1.25.4
**상태**: ✅ Production-Ready

---

## 🎯 서버 정보

| 항목 | 값 |
|------|-----|
| 서버 | 253번 (192.168.45.253) |
| 웹 포트 | 3000 (HTTP) |
| SSH 포트 | 10075 |
| 도메인 | git.dclub.kr (Nginx 리버스 프록시) |
| 데이터베이스 | SQLite3 |
| 바이너리 크기 | 109MB |

---

## 🔐 계정 정보

### 관리자 계정
```
사용자명: admin
비밀번호: admin@gitea123
이메일: admin@git.dclub.kr
```

### kim 사용자 (2026-03-01 생성)
```
사용자명: kim
이메일: kim@git.dclub.kr
API 토큰: b7cf524685f4e345b72e7667feb96b52a8cfa6a8
테스트 저장소: kim/kim-test-repo
SSH 공개 키: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL9OI98/hAnHdHkFzF+5wRhahfUK65KMHUppZSrSfy3s kim@git.dclub.kr
SSH 개인 키: ./gitea_ssh_key (chmod 600)
```

---

## 📂 디렉토리 구조

```
/home/kimjin/gitea-data/
├── gitea                  (109MB 실행 바이너리)
├── custom/
│   └── conf/
│       └── app.ini        (설정 파일)
├── gitea.db               (SQLite 데이터베이스)
└── log/
    └── gitea.log          (로그)

/home/kimjin/gitea-repos/  (저장소 저장소)
```

---

## 🚀 시작/중지

### 시작
```bash
cd /home/kimjin/gitea-data
nohup ./gitea web -c custom/conf/app.ini > log/gitea.log 2>&1 &
```

### 중지
```bash
pkill gitea
```

### 상태 확인
```bash
ps aux | grep gitea
curl http://192.168.45.253:3000/health
```

---

## 🔗 접근 방법

### 웹 인터페이스
- http://git.dclub.kr
- http://192.168.45.253:3000

### 🔑 SSH (저장소 클론) ✅ **권장**
```bash
# SSH 키 활용
GIT_SSH_COMMAND="ssh -i /home/kimjin/Desktop/kim/gitea_ssh_key" \
  git clone ssh://kimjin@192.168.45.253:10075/kim/kim-test-repo

# 또는 도메인
GIT_SSH_COMMAND="ssh -i /home/kimjin/Desktop/kim/gitea_ssh_key" \
  git clone ssh://kimjin@git.dclub.kr:10075/kim/kim-test-repo
```

**⚠️ 주의**: 사용자명은 반드시 `kimjin` (git X)

### 📋 HTTP (저장소 클론)
```bash
git clone http://git.dclub.kr/kim/kim-test-repo
```

---

## 📝 저장소 생성 (API)

### admin 토큰으로 저장소 생성
```bash
curl -X POST http://git.dclub.kr/api/v1/user/repos \
  -H "Authorization: token ee9ee02c65be2d0bdf11da0b4fffc22dc6e2a666" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "repo-name",
    "description": "설명",
    "private": false
  }'
```

### kim 토큰으로 저장소 생성
```bash
curl -X POST http://git.dcloud.kr/api/v1/user/repos \
  -H "Authorization: token b7cf524685f4e345b72e7667feb96b52a8cfa6a8" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "repo-name",
    "description": "설명",
    "private": false
  }'
```

---

## 🔑 API 토큰 생성 (CLI)

```bash
cd /home/kimjin/gitea-data

# 새 토큰 생성
./gitea admin user generate-access-token \
  -u 사용자명 \
  -t 토큰이름 \
  --raw \
  --config custom/conf/app.ini

# 예: admin 토큰
./gitea admin user generate-access-token \
  -u admin \
  -t 'my-token' \
  --raw \
  --config custom/conf/app.ini
```

---

## 🌐 Nginx 설정 (73 서버)

**파일**: `/etc/nginx/sites-enabled/git.dclub.kr.conf`

```nginx
upstream gitea {
    server 192.168.45.253:3000;
}

server {
    listen 80;
    server_name git.dclub.kr;

    location / {
        proxy_pass http://gitea;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📋 자주 쓰는 API

### 저장소 목록
```bash
curl -H "Authorization: token TOKEN" \
  http://git.dclub.kr/api/v1/user/repos
```

### 사용자 정보
```bash
curl -H "Authorization: token TOKEN" \
  http://git.dcloud.kr/api/v1/user
```

### 저장소 정보
```bash
curl http://git.dclub.kr/api/v1/repos/owner/repo
```

### 저장소 삭제
```bash
curl -X DELETE \
  -H "Authorization: token TOKEN" \
  http://git.dclub.kr/api/v1/repos/owner/repo
```

---

## 🔄 Gogs → Gitea 마이그레이션

### 다음 단계
1. Gogs에서 저장소 모두 export
2. Gitea에 import
3. SSH 키 & 토큰 설정
4. 도메인 전환 (git.dclub.kr)

---

## ⚙️ 설정 파일 (app.ini)

**경로**: `/home/kimjin/gitea-data/custom/conf/app.ini`

주요 설정:
- `PROTOCOL=http`
- `DOMAIN=git.dclub.kr`
- `ROOT_URL=http://git.dclub.kr/`
- `HTTP_ADDR=0.0.0.0`
- `HTTP_PORT=3000`
- `SSH_PORT=10075`
- `DB_TYPE=sqlite3`
- `DB_PATH=gitea.db`

---

## 📊 모니터링

### 로그 확인
```bash
tail -f /home/kimjin/gitea-data/log/gitea.log
```

### 데이터베이스 크기
```bash
ls -lh /home/kimjin/gitea-data/gitea.db
```

### 저장소 개수
```bash
ls -la /home/kimjin/gitea-repos/ | wc -l
```

---

## 🐛 트러블슈팅

### DNS 문제
현재 `/etc/hosts`에 등록:
```
192.168.45.73 git.dclub.kr
```

### 포트 충돌
```bash
# 포트 3000 확인
lsof -i :3000
netstat -tlnp | grep 3000
```

### 프로세스 재시작
```bash
pkill gitea
cd /home/kimjin/gitea-data
nohup ./gitea web -c custom/conf/app.ini > log/gitea.log 2>&1 &
```

---

## 📝 참고

- **Gogs 토큰**: d323bff42afeedf883b7052b08f0c7a8b25e851f
- **Gitea Admin 토큰**: ee9ee02c65be2d0bdf11da0b4fffc22dc6e2a666
- **Gitea kim 토큰**: b7cf524685f4e345b72e7667feb96b52a8cfa6a8
- **Gitea 공식**: https://gitea.io
- **Gitea API**: https://docs.gitea.io/en-us/api-usage/

---

**마지막 업데이트**: 2026-03-01
