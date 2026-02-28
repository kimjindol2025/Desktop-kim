#!/bin/bash

echo "⚠️ Gogs 백업 복구 도구"
echo ""
echo "사용법:"
echo "  ./gogs-backup-restore.sh [저장소명 또는 'all']"
echo ""
echo "예시:"
echo "  ./gogs-backup-restore.sh kim-pm2-cpp    # 특정 저장소만 복구"
echo "  ./gogs-backup-restore.sh all            # 모든 저장소 복구"
echo ""

if [ -z "$1" ]; then
  echo "❌ 저장소명을 입력하세요"
  exit 1
fi

BACKUP_DIR="/home/kimjin/gogs-docker/git/gogs-repositories"
SOURCE_DIR="/home/kimjin/gogs-repos"

if [ "$1" == "all" ]; then
  echo "🔄 모든 저장소를 백업에서 복구하시겠습니까? (y/n)"
  read confirm
  if [ "$confirm" != "y" ]; then
    echo "❌ 취소됨"
    exit 1
  fi
  
  rsync -av --delete $BACKUP_DIR/ $SOURCE_DIR/
  echo "✅ 모든 저장소 복구 완료"
else
  if [ ! -d "$BACKUP_DIR/$1" ]; then
    echo "❌ 저장소를 찾을 수 없음: $1"
    exit 1
  fi
  
  mkdir -p "$SOURCE_DIR/$1"
  rsync -av --delete "$BACKUP_DIR/$1/" "$SOURCE_DIR/$1/"
  echo "✅ $1 복구 완료"
fi
