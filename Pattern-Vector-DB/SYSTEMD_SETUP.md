# Pattern Vector DB - systemd 설정 가이드

## 📋 개요

Pattern Vector DB를 systemd 서비스로 실행하여 시스템 부팅 시 자동 시작, 충돌 자동 복구 등을 지원합니다.

---

## 🚀 설치 방법

### 1️⃣ 서비스 파일 설치

```bash
# 시스템 서비스 디렉토리로 복사
sudo cp pattern-vector-db.service /etc/systemd/system/

# systemd 데몬 리로드
sudo systemctl daemon-reload
```

### 2️⃣ 서비스 활성화

```bash
# 부팅 시 자동 시작 설정
sudo systemctl enable pattern-vector-db

# 서비스 시작
sudo systemctl start pattern-vector-db

# 상태 확인
sudo systemctl status pattern-vector-db
```

---

## 🎯 주요 기능

### 자동 시작
- ✅ 시스템 부팅 시 자동으로 서비스 시작
- ✅ `multi-user.target` 도달 후 시작

### 충돌 복구
- ✅ 프로세스 종료 시 자동 재시작
- ✅ 재시작 간격: 10초
- ✅ 최대 3회 재시작 (60초 내)

### 리소스 제한
- ✅ 메모리: 1GB 제한
- ✅ CPU: 75% 제한
- ✅ 최대 태스크: 512개

### 보안
- ✅ 사용자: `kimjin` (root 아님)
- ✅ 홈 디렉토리 격리
- ✅ 시스템 파일 읽기 전용
- ✅ `/logs` 디렉토리만 쓰기 허용

### 로깅
- ✅ journalctl 통합
- ✅ syslog 식별자: `pvdb`

---

## 📊 서비스 관리

### 상태 확인
```bash
# 현재 상태
systemctl status pattern-vector-db

# 로그 확인 (실시간)
journalctl -u pattern-vector-db -f

# 로그 확인 (지난 100줄)
journalctl -u pattern-vector-db -n 100

# 오류 로그만
journalctl -u pattern-vector-db -p err
```

### 서비스 제어
```bash
# 시작
sudo systemctl start pattern-vector-db

# 중지
sudo systemctl stop pattern-vector-db

# 재시작
sudo systemctl restart pattern-vector-db

# 다시 로드
sudo systemctl reload pattern-vector-db

# 자동 시작 활성화
sudo systemctl enable pattern-vector-db

# 자동 시작 비활성화
sudo systemctl disable pattern-vector-db
```

---

## 🔍 troubleshooting

### 서비스 시작 실패
```bash
# 상세 로그 확인
journalctl -u pattern-vector-db -n 50

# 서비스 파일 문법 검증
systemd-analyze verify /etc/systemd/system/pattern-vector-db.service
```

### 포트 6555 이미 사용 중
```bash
# 포트 확인
lsof -i :6555

# 다른 포트로 변경
# → pattern-vector-db.service 수정 후 systemctl restart
```

### 메모리 부족
```bash
# 현재 메모리 사용량
systemctl status pattern-vector-db

# 제한 증가
# MemoryLimit=1G → MemoryLimit=2G 변경
```

---

## 🔧 커스터마이징

### 포트 변경
```bash
# pattern-vector-db.service 편집
sudo nano /etc/systemd/system/pattern-vector-db.service

# --port 6555 → --port 7777 변경

# 변경사항 적용
sudo systemctl daemon-reload
sudo systemctl restart pattern-vector-db
```

### 워커 수 변경
```bash
# --workers 2 → --workers 4 변경
```

### 환경변수 추가
```bash
Environment="PYTHONUNBUFFERED=1"
Environment="LOG_LEVEL=debug"
```

---

## 📈 성능 모니터링

### 메트릭 확인
```bash
# CPU/메모리 사용량
systemctl status pattern-vector-db

# 상세 리소스 사용량
ps aux | grep web_dashboard

# 포트 상태
netstat -tlnp | grep 6555
```

### 헬스체크
```bash
# 서비스 응답 확인
curl http://localhost:6555/health

# 주기적 모니터링
watch -n 5 'systemctl status pattern-vector-db | head -20'
```

---

## 🔐 보안 설정

### 현재 보안 정책
- ✅ `ProtectSystem=strict` - 시스템 파일 보호
- ✅ `ProtectHome=yes` - 홈 디렉토리 보호
- ✅ `NoNewPrivileges=true` - 권한 상승 방지
- ✅ `PrivateTmp=yes` - 임시 파일 격리

### 추가 보안 옵션
```bash
# 네트워크 격리 (필요시)
PrivateDevices=yes
ProtectNetwork=yes

# 시스템 호출 필터 (고급)
SystemCallFilter=@system-service
```

---

## 🚀 자동 업데이트

### 코드 수정 후 적용
```bash
cd /home/kimjin/Pattern-Vector-DB
git pull origin master
sudo systemctl restart pattern-vector-db
```

---

## 📝 마지막 확인

```bash
# 서비스 상태
sudo systemctl status pattern-vector-db

# 로그
journalctl -u pattern-vector-db -n 20

# 포트
curl http://localhost:6555/health
```

**설정 완료!** 🎉

---

**생성일**: 2026-02-28
**버전**: 1.0.0
**상태**: Production Ready ✅
