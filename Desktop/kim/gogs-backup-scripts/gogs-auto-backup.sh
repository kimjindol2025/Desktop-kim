#!/bin/bash

set -e

# 설정
BACKUP_LOG="/home/kimjin/.gogs-backup.log"
BACKUP_STATUS="/home/kimjin/.gogs-backup.status"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BACKUP_DIR="/home/kimjin/gogs-docker/git/gogs-repositories"
PARALLEL_JOBS=4
BACKUP_TIMEOUT=300

# 함수: 로그 기록
log() {
  echo "[$TIMESTAMP] $1" >> $BACKUP_LOG
  echo "$1"
}

# 함수: 상태 파일 업데이트
update_status() {
  echo "$1" > $BACKUP_STATUS
  echo "$TIMESTAMP: $1" >> $BACKUP_LOG
}

# 시작
log "=== Gogs 자동 백업 시작 (병렬: $PARALLEL_JOBS) ==="
update_status "RUNNING"

# 1. gogs-repos 동기화
log "📦 gogs-repos 동기화..."
rsync -av --delete \
  --exclude='node_modules' \
  --exclude='.npm' \
  --exclude='target' \
  /home/kimjin/gogs-repos/ \
  $BACKUP_DIR/ \
  >> $BACKUP_LOG 2>&1 || log "⚠️ gogs-repos 동기화 부분 실패"

# 2. 모든 .git 저장소 병렬 동기화
log "🔄 전체 저장소 병렬 동기화..."

# 백업 목록 생성
find /home/kimjin -maxdepth 3 -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo_dir=$(dirname "$gitdir")
  repo_name=$(basename "$repo_dir")
  
  if [ "$repo_dir" != "/home/kimjin/gogs-repos" ]; then
    echo "$repo_dir|$repo_name"
  fi
done > /tmp/backup-list.txt

# 병렬 처리
cat /tmp/backup-list.txt | cut -d'|' -f1 | xargs -P $PARALLEL_JOBS -I {} bash << 'EOFBACKUP'
repo_dir=$1
repo_name=$(basename "$repo_dir")
timeout $BACKUP_TIMEOUT rsync -a --delete \
  --exclude='node_modules' \
  --exclude='.npm' \
  --exclude='target' \
  "$repo_dir/" \
  "$BACKUP_DIR/$repo_name/" \
  2>/dev/null || true
EOFBACKUP

# 3. 데이터베이스 동기화
log "💾 데이터베이스 검증..."
python3 << 'EOFPY'
import sqlite3
import os
from pathlib import Path

db_path = '/home/kimjin/gogs-docker/gogs/data/gogs.db'
backup_dir = '/home/kimjin/gogs-docker/git/gogs-repositories'

if os.path.exists(db_path):
  conn = sqlite3.connect(db_path)
  cursor = conn.cursor()
  
  # 파일시스템 저장소 검사
  fs_repos = set(d.name for d in Path(backup_dir).iterdir() 
                 if d.is_dir() and not d.name.startswith('.'))
  
  # DB 저장소 검사
  cursor.execute('SELECT COUNT(*) FROM repository')
  db_count = cursor.fetchone()[0]
  
  print(f"📊 백업 저장소: {len(fs_repos)}개")
  print(f"📊 DB 저장소: {db_count}개")
  
  conn.close()
else:
  print("⚠️ DB 없음")
EOFPY

# 완료
log "✅ 백업 완료"
update_status "COMPLETED"
