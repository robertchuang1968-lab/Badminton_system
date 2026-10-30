# LINE 群組羽球報名系統 - ngrok 啟動方式說明

**建立日期：2026-10-29**

---

## 正確的 ngrok 啟動方式

### ✅ 正確命令

```bash
ngrok start line-bot
```

或指定日誌：
```bash
ngrok start line-bot --log=/home/robert/workspace/LINE群組羽球報名系統/logs/ngrok.log
```

### ❌ 錯誤命令（會產生隨機域名）

```bash
ngrok http 8000  # 會忽略 ngrok.yml 配置，使用隨機域名
```

---

## 為什麼要用 `ngrok start line-bot`？

| 命令 | 行為 |
|------|------|
| `ngrok start line-bot` | 讀取 `ngrok.yml` 中的「line-bot」tunnel 配置，使用固定域名 |
| `ngrok http 8000` | 建立命令列暫存 tunnel，使用隨機域名（每次不同） |

---

## 配置檔案位置

- **系統配置**: `~/.config/ngrok/ngrok.yml`
- **專案配置**: `/home/robert/workspace/LINE群組羽球報名系統/ngrok.yml`

兩個配置檔案都定義了相同的 tunnel：
```yaml
tunnels:
  line-bot:
    addr: 8000
    proto: http
    domain: platypus-flexible-buck.ngrok-free.app
```

---

## LINE Webhook URL

**固定網址**（不得更改）：
```
https://platypus-flexible-buck.ngrok-free.app/webhook/line
```

---

## 啟動腳本

### 使用方法

```bash
cd /home/robert/workspace/LINE群組羽球報名系統

./start_server.sh start      # 啟動所有服務
./start_server.sh stop       # 停止所有服務
./start_server.sh status     # 查看狀態
./start_server.sh restart    # 重新啟動
```

### 功能說明

| 功能 | 說明 |
|------|------|
| 自動檢測現狀 | 若服務已在運行，跳過啟動避免重複 |
| 健康檢查 | 確認 webhook URL 可達 |
| PID 記錄 | 寫入 `logs/pids/` 目錄 |
| 日誌分離 | uvicorn → `logs/uvicorn.log`，ngrok → `logs/ngrok.log` |

**檢測邏輯：**
- uvicorn：`pgrep -f "uvicorn app.main"`
- ngrok：`curl http://localhost:4040/api/tunnels` 確認是否已有固定域名 tunnel

### 測試結果

| 情境 | uvicorn | ngrok | 結果 |
|------|---------|-------|------|
| 兩者都斷線 | ❌ | ❌ | 同時啟動兩個 ✓ |
| 只有 uvicorn 斷線 | ❌ | ✅ | **只重啟 uvicorn** ✓ |
| 只有 ngrok 斷線 | ✅ | ❌ | **只重啟 ngrok** ✓ |
| 兩者都在運行 | ✅ | ✅ | 跳過，顯示現狀 ✓ |

**測試日期：** 2026-10-29
**測試方法：**
1. 手動 kill uvicorn → 執行 `./start_server.sh start` → 確認只重啟 uvicorn
2. 手動 kill ngrok → 執行 `./start_server.sh start` → 確認只重啟 ngrok

---

## 補充說明（2026-10-29）

### 同一日期多場次處理

若同一日期有多個場次（上午 + 下午），會產生兩個 Excel 檔案：
- `2026_10_31-AM.xlsx` → 上午場
- `2026_10_31-PM.xlsx` → 下午場

**注意：** 若先貼下午場公告再貼上午場公告，會同時存在兩個檔案。建議刪除錯誤的檔案。

### 日誌檔案路徑

- uvicorn log: `logs/uvicorn.log`
- ngrok log: `logs/ngrok.log`
- PID 記錄: `logs/pids/`

---

## 常見問題

### Q: 為什麼 ngrok 會產生隨機域名？
A: 使用了 `ngrok http 8000` 而非 `ngrok start line-bot`。前者會忽略配置文件，後者才會讀取 domain 設定。

### Q: 如何確認 ngrok 正在使用固定域名？
A: 執行 `curl http://localhost:4040/api/tunnels` 查看 public_url 是否為 `https://platypus-flexible-buck.ngrok-free.app`

### Q: 修改配置後如何重啟？
A: 先 `pkill ngrok`，然後重新執行 `ngrok start line-bot`

### Q: 執行 start 時會不會啟動多個 ngrok？
A: 不會。腳本會先檢查是否有固定域名的 tunnel 存在，若有則跳過啟動。

---

*記錄時間：2026-10-29*
