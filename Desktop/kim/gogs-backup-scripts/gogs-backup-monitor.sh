#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Gogs 백업 자동화 모니터링 대시보드                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 서비스 상태
echo "📋 서비스 상태:"
sudo systemctl is-active gogs-backup.service 2>/dev/null && echo "  ✅ 서비스: 활성" || echo "  ❌ 서비스: 비활성"
sudo systemctl is-enabled gogs-backup.timer 2>/dev/null && echo "  ✅ Timer: 활성" || echo "  ❌ Timer: 비활성"

# 2. 마지막 백업 상태
echo ""
echo "📊 마지막 백업:"
if [ -f /home/kimjin/.gogs-backup.status ]; then
  status=$(cat /home/kimjin/.gogs-backup.status)
  echo "  상태: $status"
fi

# 3. 백업 통계
echo ""
echo "💾 백업 통계:"
echo "  원본 크기: $(du -sh /home/kimjin/gogs-repos 2>/dev/null | cut -f1)"
echo "  백업 크기: $(du -sh /home/kimjin/gogs-docker/git/gogs-repositories 2>/dev/null | cut -f1)"

# 4. 저장소 개수
echo ""
echo "📦 저장소 개수:"
echo "  원본: $(ls -1d /home/kimjin/gogs-repos/*/ 2>/dev/null | wc -l)개"
echo "  백업: $(ls -1d /home/kimjin/gogs-docker/git/gogs-repositories/*/ 2>/dev/null | wc -l)개"

# 5. 다음 백업
echo ""
echo "⏰ 다음 백업:"
next_backup=$(sudo systemctl status gogs-backup.timer 2>/dev/null | grep -i "trigger" | head -1)
echo "  $next_backup"

# 6. 최근 로그
echo ""
echo "📝 최근 로그:"
tail -5 /home/kimjin/.gogs-backup.log 2>/dev/null || echo "  (로그 없음)"
