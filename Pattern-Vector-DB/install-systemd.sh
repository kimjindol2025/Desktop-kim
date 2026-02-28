#!/bin/bash
# Pattern Vector DB - systemd 서비스 자동 설치 스크립트

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pattern-vector-db"
SERVICE_FILE="${PROJECT_ROOT}/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=========================================="
echo "Pattern Vector DB - systemd 설치"
echo "=========================================="
echo ""

# 1. 권한 확인
if [[ $EUID -ne 0 ]]; then
   echo "❌ 이 스크립트는 root 권한으로 실행해야 합니다"
   echo "   실행: sudo bash install-systemd.sh"
   exit 1
fi

# 2. 서비스 파일 확인
if [[ ! -f "$SERVICE_FILE" ]]; then
   echo "❌ 서비스 파일을 찾을 수 없습니다: $SERVICE_FILE"
   exit 1
fi

echo "✅ 서비스 파일 확인됨: $SERVICE_FILE"
echo ""

# 3. 기존 서비스 중지 (있으면)
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
   echo "⏹️  기존 서비스 중지 중..."
   systemctl stop $SERVICE_NAME
   sleep 2
fi

# 4. 서비스 파일 설치
echo "📝 systemd에 서비스 파일 설치 중..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
echo "✅ 설치 완료: $SYSTEMD_DIR/$SERVICE_NAME.service"
echo ""

# 5. systemd 리로드
echo "🔄 systemd 데몬 리로드 중..."
systemctl daemon-reload
echo "✅ 리로드 완료"
echo ""

# 6. 자동 시작 활성화
echo "🚀 자동 시작 활성화 중..."
systemctl enable $SERVICE_NAME
echo "✅ 활성화 완료"
echo ""

# 7. 서비스 시작
echo "▶️  서비스 시작 중..."
systemctl start $SERVICE_NAME
sleep 2

# 8. 상태 확인
echo "📊 서비스 상태:"
systemctl status $SERVICE_NAME --no-pager | head -10
echo ""

# 9. 포트 확인
echo "🔌 포트 상태:"
if netstat -tlnp 2>/dev/null | grep -q 6555; then
   echo "✅ 포트 6555 열려있음"
else
   echo "⏳ 포트 6555 시작 대기 중..."
   sleep 3
fi

# 10. 헬스체크
echo ""
echo "💗 헬스체크:"
if curl -s http://localhost:6555/health > /dev/null 2>&1; then
   echo "✅ 서비스가 정상 작동 중입니다"
else
   echo "⚠️  서비스가 아직 시작 중입니다 (로그 확인: journalctl -u pattern-vector-db -f)"
fi

echo ""
echo "=========================================="
echo "✅ 설치 완료!"
echo "=========================================="
echo ""
echo "📚 주요 명령어:"
echo "  상태 확인:    systemctl status pattern-vector-db"
echo "  로그 확인:    journalctl -u pattern-vector-db -f"
echo "  서비스 중지:  sudo systemctl stop pattern-vector-db"
echo "  서비스 재시작: sudo systemctl restart pattern-vector-db"
echo ""
echo "📖 상세 가이드: SYSTEMD_SETUP.md 참조"
echo ""
