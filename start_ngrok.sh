#!/bin/bash
# LINE Bot ngrok 啟動腳本（WSL 版本）
# 用法: ./start_ngrok.sh

set -e

PROJECT_DIR="/home/robert/workspace/LINE群組羽球報名系統"
NGROK_BIN="/home/robert/bin/ngrok"
NGROK_CONFIG="$PROJECT_DIR/ngrok.yml"
LOG_FILE="$PROJECT_DIR/logs/ngrok.log"

echo "=== LINE Bot ngrok 啟動 ==="
echo ""

# 檢查 ngrok 是否已安裝
if [ ! -f "$NGROK_BIN" ]; then
    echo "❌ ngrok 未安裝: $NGROK_BIN"
    exit 1
fi

# 確保 logs 目錄存在
mkdir -p "$PROJECT_DIR/logs"

# 檢查是否有現有的 ngrok 進程
if pgrep -f "ngrok start line-bot" > /dev/null; then
    echo "⚠️  ngrok 已在運行中"
    echo "   先停止現有進程..."
    pkill -f "ngrok start line-bot"
    sleep 2
fi

# 啟動 ngrok
echo "🚀 啟動 ngrok tunnel..."
echo ""
$NGROK_BIN start line-bot --log="$LOG_FILE" &
NGROK_PID=$!

# 等待啟動
sleep 3

# 檢查狀態
if curl -s http://127.0.0.1:4040/api/tunnels > /dev/null 2>&1; then
    echo "✅ ngrok 啟動成功！"
    echo ""
    echo "Tunnel URL:"
    curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tunnels', []):
    print(f'  {t[\"public_url\"]}')
    print(f'  Webhook: {t[\"public_url\"]}/webhook/line')
"
    echo ""
    echo "PID: $NGROK_PID"
    echo "Log: $LOG_FILE"
else
    echo "❌ ngrok 啟動失敗，請檢查日誌: $LOG_FILE"
    exit 1
fi
