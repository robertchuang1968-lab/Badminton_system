#!/bin/bash
# cloudflared 管理腳本 - 使用 PID 文件避免重複進程
set -e

PROJECT_DIR="/mnt/c/Users/rober/Desktop/LINE群組羽球報名系統"
PID_FILE="$PROJECT_DIR/.cloudflared.pid"
LOG_FILE="$PROJECT_DIR/logs/cloudflared.log"
CLOUDFLARED="$PROJECT_DIR/tools/cloudflared"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Cloudflared 正在運行 (PID: $PID)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  PID 文件存在但進程已結束，清理殘留文件${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

start() {
    if check_process; then
        echo -e "${YELLOW}ℹ️  Cloudflared 已在運行中，無需再次啟動${NC}"
        exit 0
    fi
    
    echo -e "${GREEN}🚀 啟動 Cloudflared Tunnel...${NC}"
    
    # 確保日誌目錄存在
    mkdir -p "$PROJECT_DIR/logs"
    
    # 啟動進程並保存 PID
    nohup "$CLOUDFLARED" tunnel --url http://localhost:8000 >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"
    
    echo -e "${GREEN}✅ Cloudflared 已啟動 (PID: $NEW_PID)${NC}"
    echo "📄 日誌文件: $LOG_FILE"
    echo "📋 PID 文件: $PID_FILE"
    
    # 等待幾秒確認運行
    sleep 3
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 進程運行正常${NC}"
    else
        echo -e "${RED}❌ 啟動失敗，請查看日誌${NC}"
        exit 1
    fi
}

stop() {
    if check_process; then
        PID=$(cat "$PID_FILE")
        echo -e "${YELLOW}⏹️  停止 Cloudflared (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null || true
        
        # 等待進程結束
        for i in $(seq 1 10); do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 如果還在運行，強制終止
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  強制終止進程...${NC}"
            kill -9 "$PID" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        echo -e "${GREEN}✅ Cloudflared 已停止${NC}"
    else
        echo -e "${YELLOW}ℹ️  Cloudflared 未在運行${NC}"
    fi
}

restart() {
    stop
    sleep 2
    start
}

status() {
    echo -e "=== Cloudflared 狀態 ==="
    if check_process; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}狀態: 運行中${NC}"
        echo -e "PID: $PID"
        echo -e "啟動時間: $(ps -o lstart= -p $PID 2>/dev/null || echo '未知')"
    else
        echo -e "${RED}狀態: 未運行${NC}"
    fi
    echo ""
    echo "PID 文件: $PID_FILE"
    echo "日誌文件: $LOG_FILE"
}

case "${1:-status}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
