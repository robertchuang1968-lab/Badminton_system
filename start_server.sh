#!/bin/bash
# LINE 群組羽球報名系統 - 完整啟動腳本
# 用法: ./start_server.sh [start|stop|status]

set -e

PROJECT_DIR="/home/robert/workspace/LINE群組羽球報名系統"
UVICORN_BIN="/home/robert/.hermes/hermes-agent/venv/bin/python"
NGROK_BIN="/home/robert/bin/ngrok"
LOG_DIR="$PROJECT_DIR/logs"
UVICORN_LOG="$LOG_DIR/uvicorn.log"
NGROK_LOG="$LOG_DIR/ngrok.log"
PID_DIR="$LOG_DIR/pids"

# 確保目錄存在
mkdir -p "$LOG_DIR" "$PID_DIR"

# ==================== 函數 ====================

start_uvicorn() {
    if pgrep -f "uvicorn app.main" > /dev/null; then
        echo "⚠️  uvicorn 已在運行中 (PID: $(pgrep -f 'uvicorn app.main'))"
        return 0
    fi
    
    echo "🚀 啟動 uvicorn..."
    cd "$PROJECT_DIR"
    nohup $UVICORN_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
        > "$UVICORN_LOG" 2>&1 &
    echo $! > "$PID_DIR/uvicorn.pid"
    sleep 2
    
    if pgrep -f "uvicorn app.main" > /dev/null; then
        echo "✅ uvicorn 啟動成功 (PID: $(cat $PID_DIR/uvicorn.pid))"
    else
        echo "❌ uvicorn 啟動失敗"
        return 1
    fi
}

start_ngrok() {
    # 使用更寬鬆的檢測方式（兼容 "ngrok start line-bot" 和 "ngrok start --all"）
    if pgrep -f "ngrok" > /dev/null 2>&1 && pgrep -f "ngrok" | grep -q "[0-9]"; then
        # 確認是否有穩定的 tunnel
        if curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -q "platypus-flexible-buck"; then
            echo "⚠️  ngrok 已在運行中（固定域名）"
            return 0
        fi
    fi
    
    echo "🚀 啟動 ngrok..."
    nohup $NGROK_BIN start line-bot --log="$NGROK_LOG" > /dev/null 2>&1 &
    sleep 3
    
    # 檢查健康狀態
    if curl -s http://localhost:4040/api/tunnels | grep -q "platypus-flexible-buck"; then
        TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tunnels', []):
    if 'platypus-flexible-buck' in t['public_url']:
        print(t['public_url'])
        break
")
        echo "✅ ngrok 啟動成功"
        echo "   Tunnel: $TUNNEL_URL"
        echo "   Webhook: $TUNNEL_URL/webhook/line"
    else
        echo "❌ ngrok 啟動失敗或域名不正確"
        return 1
    fi
}

stop_services() {
    echo "🛑 停止所有服務..."
    
    if pgrep -f "uvicorn app.main" > /dev/null; then
        pkill -f "uvicorn app.main"
        echo "  ✓ uvicorn 已停止"
    fi
    
    if pgrep -f "ngrok" > /dev/null; then
        pkill -f "ngrok"
        echo "  ✓ ngrok 已停止"
    fi
    
    echo "✅ 所有服務已停止"
}

show_status() {
    echo "=== 服務狀態 ==="
    echo ""
    
    # uvicorn
    if pgrep -f "uvicorn app.main" > /dev/null; then
        echo "✅ uvicorn: 運行中 (PID: $(pgrep -f 'uvicorn app.main'))"
    else
        echo "❌ uvicorn: 未運行"
    fi
    
    # ngrok
    if pgrep -f "ngrok" > /dev/null; then
        echo "✅ ngrok: 運行中"
        curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
        print(f\"   Tunnel: {t['public_url']}\")
except:
    print('   (無法獲取 tunnel 資訊)')
"
    else
        echo "❌ ngrok: 未運行"
    fi
    
    echo ""
    echo "=== 健康檢查 ==="
    HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"status":"error"}')
    if echo "$HEALTH" | grep -q '"healthy"'; then
        echo "✅ Webhook: https://platypus-flexible-buck.ngrok-free.app/webhook/line"
    else
        echo "⚠️  健康檢查失敗"
    fi
}

# ==================== 主程式 ====================

case "${1:-start}" in
    start)
        echo "=== LINE 群組羽球報名系統啟動 ==="
        echo ""
        start_uvicorn
        echo ""
        start_ngrok
        echo ""
        show_status
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    restart)
        stop_services
        sleep 2
        $0 start
        ;;
    *)
        echo "用法: $0 [start|stop|status|restart]"
        echo ""
        echo "  start   - 啟動所有服務（預設）"
        echo "  stop    - 停止所有服務"
        echo "  status  - 顯示服務狀態"
        echo "  restart - 重新啟動所有服務"
        exit 1
        ;;
esac
