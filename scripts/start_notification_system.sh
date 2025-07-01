#!/bin/bash

# AIGEN Science 알림 시스템 관리 스크립트

SCRIPT_DIR="/home/br631533333333_gmail_com/Aigen_science"
PID_FILE="$SCRIPT_DIR/notification_system.pid"
LOG_FILE="$SCRIPT_DIR/notification_system.log"

case "$1" in
    start)
        echo "🚀 AIGEN Science 알림 시스템 시작 중..."
        
        # 이미 실행 중인지 확인
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                echo "❌ 이미 실행 중입니다. (PID: $PID)"
                exit 1
            else
                echo "⚠️  이전 PID 파일을 정리합니다."
                rm -f "$PID_FILE"
            fi
        fi
        
        # Python 환경 확인
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python3가 설치되지 않았습니다."
            exit 1
        fi
        
        # 의존성 확인
        cd "$SCRIPT_DIR"
        if ! python3 -c "import schedule, requests, sib_api_v3_sdk, supabase" 2>/dev/null; then
            echo "❌ 필요한 Python 패키지가 설치되지 않았습니다."
            echo "다음 명령어로 설치하세요:"
            echo "pip install schedule sib-api-v3-sdk supabase requests python-dotenv"
            exit 1
        fi
        
        # 백그라운드에서 실행
        nohup python3 "$SCRIPT_DIR/simple_notification_system.py" > "$LOG_FILE" 2>&1 &
        PID=$!
        echo $PID > "$PID_FILE"
        
        echo "✅ 알림 시스템이 시작되었습니다. (PID: $PID)"
        echo "📝 로그 파일: $LOG_FILE"
        echo "🔍 상태 확인: $0 status"
        ;;
        
    stop)
        echo "🛑 AIGEN Science 알림 시스템 중지 중..."
        
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                kill $PID
                echo "✅ 알림 시스템이 중지되었습니다. (PID: $PID)"
            else
                echo "⚠️  프로세스가 이미 종료되었습니다."
            fi
            rm -f "$PID_FILE"
        else
            echo "❌ PID 파일을 찾을 수 없습니다."
        fi
        ;;
        
    restart)
        echo "🔄 AIGEN Science 알림 시스템 재시작 중..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "📊 AIGEN Science 알림 시스템 상태:"
        
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ 실행 중 (PID: $PID)"
                echo "📝 로그 파일: $LOG_FILE"
                if [ -f "$LOG_FILE" ]; then
                    echo "📄 최근 로그 (마지막 10줄):"
                    tail -n 10 "$LOG_FILE"
                fi
            else
                echo "❌ 중지됨 (PID 파일은 존재하지만 프로세스 없음)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ 중지됨 (PID 파일 없음)"
        fi
        
        # 뉴스 추천 API 상태 확인
        echo ""
        echo "🔗 뉴스 추천 API 상태:"
        if curl -s http://34.61.170.171:8001/recommendations > /dev/null 2>&1; then
            echo "✅ 연결됨"
        else
            echo "❌ 연결 실패"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            echo "📄 알림 시스템 로그:"
            tail -f "$LOG_FILE"
        else
            echo "❌ 로그 파일을 찾을 수 없습니다."
        fi
        ;;
        
    install-service)
        echo "🔧 systemd 서비스 설치 중..."
        
        if [ "$EUID" -ne 0 ]; then
            echo "❌ root 권한이 필요합니다."
            exit 1
        fi
        
        SERVICE_FILE="/etc/systemd/system/aigen-notification.service"
        
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AIGEN Science Notification System
After=network.target

[Service]
Type=simple
User=br631533333333_gmail_com
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/simple_notification_system.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable aigen-notification.service
        
        echo "✅ systemd 서비스가 설치되었습니다."
        echo "시작: sudo systemctl start aigen-notification"
        echo "상태: sudo systemctl status aigen-notification"
        echo "로그: sudo journalctl -u aigen-notification -f"
        ;;
        
    *)
        echo "AIGEN Science 알림 시스템 관리 스크립트"
        echo ""
        echo "사용법: $0 {start|stop|restart|status|logs|install-service}"
        echo ""
        echo "명령어:"
        echo "  start          - 알림 시스템 시작"
        echo "  stop           - 알림 시스템 중지"
        echo "  restart        - 알림 시스템 재시작"
        echo "  status         - 상태 확인"
        echo "  logs           - 실시간 로그 보기"
        echo "  install-service - systemd 서비스로 설치"
        echo ""
        echo "예시:"
        echo "  $0 start       # 시작"
        echo "  $0 status      # 상태 확인"
        echo "  $0 logs        # 로그 보기"
        ;;
esac 