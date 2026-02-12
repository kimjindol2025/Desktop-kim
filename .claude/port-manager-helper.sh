#!/bin/bash
#
# Port Manager 헬퍼 - Claude Code 자동 포트 할당
# 버전: 2.0 (2026-02-05 업데이트)
#
# 사용:
#   source /home/kimjin/.claude/port-manager-helper.sh
#   pm_start "app-name" "PORT={port} npm start" "개발 중"
#   pm_list
#   pm_stop 1
#

PM_API="http://localhost:45000"

# Claude Code 세션 정보 추출
CLAUDE_PID=$$ # 현재 쉘의 PID
CLAUDE_SESSION_ID="${CLAUDE_SESSION_ID:-claude-code-$(date +%s)}"  # 자동 생성

# ============================================
# 1️⃣ 서버 시작 (포트 자동 할당)
# ============================================

pm_start() {
  local name="$1"
  local command="$2"
  local reason="$3"
  local duration="${4:-1}"
  local tags="${5:-}"

  if [ -z "$name" ] || [ -z "$command" ] || [ -z "$reason" ]; then
    echo "❌ 사용: pm_start NAME COMMAND REASON [DURATION] [TAGS]"
    echo ""
    echo "예시:"
    echo "  pm_start 'my-api' 'PORT={port} npm start' 'API 서버 개발' 1 'nodejs,api'"
    echo ""
    echo "파라미터:"
    echo "  NAME: 앱 이름 (필수, 영문/숫자/하이픈)"
    echo "  COMMAND: 실행 명령어 (필수, {port} 플레이스홀더 필수)"
    echo "  REASON: 할당 사유 (필수)"
    echo "  DURATION: 기간 (선택, 기본값 1)"
    echo "    1 = 1일"
    echo "    2 = 7일"
    echo "    3 = 30일"
    echo "    4 = 무제한"
    echo "  TAGS: 태그 (선택, 콤마 구분)"
    return 1
  fi

  # {port} 플레이스홀더 확인
  if [[ ! "$command" =~ \{port\} ]]; then
    echo "❌ command에 {port} 플레이스홀더가 필수입니다"
    return 1
  fi

  echo "🚀 서버 시작 중... ($name)"
  echo "  명령어: $command"
  echo "  사유: $reason"
  echo ""

  # API 호출
  local json_payload=$(cat <<EOF
{
  "name": "$name",
  "command": "$command",
  "reason": "$reason",
  "duration": $duration
  $([ -n "$tags" ] && echo ", \"tags\": \"$tags\"" || true)
}
EOF
)

  local response=$(curl -s -X POST "$PM_API/api/servers/start" \
    -H "Content-Type: application/json" \
    -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
    -H "X-Claude-PID: $CLAUDE_PID" \
    -d "$json_payload")

  # 응답 파싱
  local success=$(echo "$response" | jq -r '.success // false' 2>/dev/null)
  local port=$(echo "$response" | jq -r '.port // empty' 2>/dev/null)
  local server_id=$(echo "$response" | jq -r '.server_id // empty' 2>/dev/null)
  local error=$(echo "$response" | jq -r '.error // empty' 2>/dev/null)

  if [ "$success" == "true" ] && [ -n "$port" ]; then
    echo "✅ 서버 시작 완료!"
    echo "   Server ID: $server_id"
    echo "   포트: $port"
    echo "   URL: http://localhost:$port"
    echo ""

    # Phase 5: 배포 질문 (duration=4인 경우만)
    if [ "$duration" == "4" ]; then
      echo "🌐 도메인 배포하시겠습니까? (y/n): "
      read -r deploy_choice

      if [[ "$deploy_choice" == "y" || "$deploy_choice" == "Y" ]]; then
        read -p "서브도메인 입력 (예: myapp): " subdomain

        if [ -n "$subdomain" ]; then
          echo "📤 DNS Manager 호출 중..."

          local deploy_payload=$(cat <<EOF2
{
  "name": "$name",
  "command": "$command",
  "reason": "$reason",
  "duration": $duration,
  "deploy": true,
  "subdomain": "$subdomain",
  "server": "253"
  $([ -n "$tags" ] && echo ", \"tags\": \"$tags\"" || true)
}
EOF2
)

          local deploy_response=$(curl -s -X POST "$PM_API/api/servers/start" \
            -H "Content-Type: application/json" \
            -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
            -H "X-Claude-PID: $CLAUDE_PID" \
            -d "$deploy_payload")

          local deploy_success=$(echo "$deploy_response" | jq -r '.deployment.success // false' 2>/dev/null)

          if [ "$deploy_success" == "true" ]; then
            echo "✅ 배포 완료!"
            echo "   도메인: https://$subdomain.dclub.kr"
            echo "   포트: $port (무제한)"
          else
            echo "⚠️  배포 실패 (수동 설정 필요)"
            echo "$deploy_response" | jq '.deployment' 2>/dev/null || echo "$deploy_response"
          fi
        fi
      fi
    fi

    echo ""

    # 헬스 체크
    sleep 2
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
      echo "✅ 헬스 체크: OK"
    else
      echo "⏳ 헬스 체크: 타임아웃 (앱 시작 중일 수 있음)"
    fi

    return 0
  else
    echo "❌ 포트 할당 실패"
    if [ -n "$error" ]; then
      echo "   에러: $error"
    fi
    echo ""
    echo "API 응답:"
    echo "$response" | jq . 2>/dev/null || echo "$response"
    return 1
  fi
}

# ============================================
# 2️⃣ 서버 목록 조회
# ============================================

pm_list() {
  local status="${1:-}"

  echo "📋 실행 중인 서버 목록"
  echo "======================"
  echo ""

  local query=""
  if [ -n "$status" ]; then
    query="?status=$status"
  fi

  local response=$(curl -s "$PM_API/api/servers$query" \
    -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
    -H "X-Claude-PID: $CLAUDE_PID" \
)

  local count=$(echo "$response" | jq '.servers | length' 2>/dev/null)

  if [ "$count" -eq 0 ]; then
    echo "실행 중인 서버가 없습니다"
    return 0
  fi

  echo "$response" | jq -r '.servers[] |
    "\(.id | tostring | rjust(3)) | \(.name | ljust(30)) | \(.port | tostring | rjust(5)) | \(.status)"' 2>/dev/null || {
    echo "$response" | jq '.servers'
  }

  echo ""
  echo "총 $count개 서버"
}

# ============================================
# 3️⃣ 서버 중지
# ============================================

pm_stop() {
  local server_id="$1"

  if [ -z "$server_id" ]; then
    echo "❌ 사용: pm_stop SERVER_ID"
    echo ""
    echo "예시: pm_stop 1"
    echo ""
    echo "Server ID 확인:"
    pm_list
    return 1
  fi

  echo "⏹️  서버 중지 중... (ID: $server_id)"

  local response=$(curl -s -X POST "$PM_API/api/servers/$server_id/stop" \
    -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
    -H "X-Claude-PID: $CLAUDE_PID" \
)

  local success=$(echo "$response" | jq -r '.success // false' 2>/dev/null)

  if [ "$success" == "true" ]; then
    echo "✅ 서버 중지 완료"
    return 0
  else
    echo "❌ 서버 중지 실패"
    echo "$response" | jq .
    return 1
  fi
}

# ============================================
# 4️⃣ 서버 취소 (중지 + 포트 해제)
# ============================================

pm_cancel() {
  local server_id="$1"

  if [ -z "$server_id" ]; then
    echo "❌ 사용: pm_cancel SERVER_ID"
    return 1
  fi

  echo "🗑️  서버 취소 중... (ID: $server_id)"

  local response=$(curl -s -X POST "$PM_API/api/servers/$server_id/cancel" \
    -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
    -H "X-Claude-PID: $CLAUDE_PID" \
)

  local success=$(echo "$response" | jq -r '.success // false' 2>/dev/null)

  if [ "$success" == "true" ]; then
    echo "✅ 서버 취소 완료 (포트 해제됨)"
    return 0
  else
    echo "❌ 취소 실패"
    echo "$response" | jq .
    return 1
  fi
}

# ============================================
# 5️⃣ 포트 현황
# ============================================

pm_ports() {
  echo "🔌 사용 중인 포트 목록"
  echo "===================="
  echo ""

  local response=$(curl -s "$PM_API/api/ports/used" \
    -H "X-Claude-Session-ID: $CLAUDE_SESSION_ID" \
    -H "X-Claude-PID: $CLAUDE_PID" \
)

  echo "$response" | jq -r '.ports[]' 2>/dev/null | sort -n | \
    awk '{if(NR%5==1) printf "\n"; printf "%5d  ", $0} END {print ""}'
}

# ============================================
# 6️⃣ Port Manager 상태
# ============================================

pm_health() {
  echo "🏥 Port Manager 헬스 체크"
  echo "========================"
  echo ""

  local health=$(curl -s "$PM_API/health")
  echo "$health" | jq .

  echo ""
  echo "📊 통계"
  echo "-----"

  local stats=$(curl -s "$PM_API/api/stats")
  echo "$stats" | jq '.stats.port_management'
}

# ============================================
# 도움말
# ============================================

pm_help() {
  cat << 'EOF'
🚀 Port Manager Helper v2.0

명령어:
  pm_start NAME CMD REASON [DURATION] [TAGS]  - 서버 시작 (포트 자동 할당)
  pm_list [STATUS]                             - 서버 목록 조회
  pm_stop SERVER_ID                            - 서버 중지
  pm_cancel SERVER_ID                          - 서버 취소 (포트 해제)
  pm_ports                                     - 사용 중인 포트 목록
  pm_health                                    - Port Manager 상태 확인
  pm_help                                      - 이 도움말

예시:

1️⃣ Node.js 앱 시작
   pm_start "my-api" "PORT={port} npm start" "API 서버" 1 "nodejs,api"

2️⃣ Python 앱 시작
   pm_start "my-flask" "flask run --port {port}" "Flask 개발" 1 "python"

3️⃣ 서버 목록 확인
   pm_list
   pm_list RUNNING

4️⃣ 서버 중지 및 취소
   pm_stop 1        # 중지 (포트 유지)
   pm_cancel 1      # 취소 (포트 해제)

5️⃣ 포트 현황
   pm_ports

기간 (duration):
  1 = 1일
  2 = 7일
  3 = 30일
  4 = 무제한 (기본값 권장 안 함)

필수 조건:
  - PORT={port} 플레이스홀더 반드시 포함
  - reason (할당 사유) 필수 기입
  - 내부 로컬호스트 전용 (인증 불필요)

위치: /home/kimjin/.claude/port-manager-helper.sh
EOF
}

# ============================================
# 초기화 메시지
# ============================================

if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
  # 직접 실행된 경우
  pm_health
else
  # source로 로드된 경우
  echo "✅ Port Manager Helper 로드됨"
  echo "   명령어: pm_start, pm_list, pm_stop, pm_cancel, pm_ports, pm_health, pm_help"
fi
