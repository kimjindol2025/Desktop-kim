# Gogs 자동 백업 시스템 설정

**작성일**: 2026-03-01  
**상태**: ✅ 완성

## 개요

- **원본**: gogs.dclub.kr (73번) - 121개 저장소
- **백업**: gogs253.dclub.kr (253번) - 121개 저장소
- **자동화**: 매시간 자동 백업

## 구성 요소

### 1. 메인 백업 스크립트
```bash
/home/kimjin/gogs-auto-backup.sh
```

**기능**:
- 병렬 처리 (4개 저장소 동시)
- 증분 백업 (변경된 파일만)
- 제외 항목: `node_modules`, `.npm`, `target`
- 자동 로깅 및 상태 추적

### 2. 자동 실행 (Cron)
```bash
0 * * * * /home/kimjin/gogs-auto-backup.sh
```

**주기**: 매시간 정각 (00:00, 01:00, 02:00...)

### 3. 모니터링 도구
```bash
/home/kimjin/gogs-backup-monitor.sh
```

**표시 항목**:
- 서비스 상태
- 마지막 백업 결과
- 백업/원본 크기
- 저장소 개수
- 다음 백업 시간

### 4. 복구 도구
```bash
/home/kimjin/gogs-backup-restore.sh [저장소|all]
```

**용도**:
- 특정 저장소만 복구
- 전체 저장소 복구
- 손상된 저장소 복구

## 사용 방법

### 상태 확인
```bash
/home/kimjin/gogs-backup-monitor.sh
```

### 수동 백업 실행
```bash
/home/kimjin/gogs-auto-backup.sh
```

### 특정 저장소 복구
```bash
/home/kimjin/gogs-backup-restore.sh kim-pm2-cpp
```

### 전체 저장소 복구
```bash
/home/kimjin/gogs-backup-restore.sh all
```

### 로그 실시간 모니터링
```bash
tail -f /home/kimjin/.gogs-backup.log
```

## 현재 상태

| 항목 | 상태 |
|------|------|
| 원본 저장소 | 121개 |
| 백업 저장소 | 121개 ✅ |
| 백업 크기 | ~112GB |
| 자동 실행 | Cron ✅ |
| 마지막 백업 | 2026-03-01 08:12 |

## 백업 위치

```
원본:  /home/kimjin/gogs-repos + /home/kimjin/*.git
백업:  /home/kimjin/gogs-docker/git/gogs-repositories
로그:  /home/kimjin/.gogs-backup.log
상태:  /home/kimjin/.gogs-backup.status
```

## 주요 기능

✅ **자동 백업** - 매시간 손이 가지 않음  
✅ **병렬 처리** - 빠른 백업 (4개 동시)  
✅ **증분 백업** - 용량 절감  
✅ **자동 로깅** - 모든 작업 기록  
✅ **상태 추적** - RUNNING/COMPLETED  
✅ **복구 기능** - 선택적 또는 전체 복구  
✅ **모니터링** - 실시간 대시보드  

## 설정 히스토리

1. **2026-02-28** - Gogs 253 배포 및 인증 문제 해결
2. **2026-03-01** - 73번 ↔ 253번 저장소 동기화
3. **2026-03-01** - 자동화 백업 시스템 구현

---

**관리자**: Claude Code  
**최종 업데이트**: 2026-03-01 08:12
