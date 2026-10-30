# LINE 群組羽球報名系統規格 v1.2

> 版本日期：2026-10-21
> 原始版本：LINE 群組羽球報名系統規格（v11）
> 變更說明：新增「偵錯記錄」與「已知坑點」章節，記錄 ngrok 認證、handler 註冊錯誤、uvicorn reload 等實戰問題

---

## 1. 功能說明

### 1.1 手動功能：新場次公告

**觸發條件**：在 LINE 群組上發布羽球訊息（附 1）

**系統行為**：
1. 系統讀取訊息，搜尋以下 key-word：
   - 日期 Date（ex. 10/9）
   - 場次 Court（ex. 上午場/下午場）
   - 場地 Site（ex. XX 羽球館）
   - 時間 Time（ex. 9:00~12:00）
   - 名單 Name_List（格式為 Pandas DataFrame，附 2）
2. 若無法獲取上述完整內容，則視為一般聊天訊息，系統不處理
3. 檢查是否為新開場次（對應 Excel 檔案不存在）
4. Excel 檔案命名規則：
   - 將日期 Date 拆成 Mon, Day 2 個參數
   - 取當天日期 (Today) 的年份 Year
   - 若 Year/Mon/Day < Today，則檔案名 = `(Year+1)_Mon_Day-Court.xlsx`
   - 否則檔案名 = `Year_Mon_Day-Court.xlsx`
   - Court=AM（上午場）；Court=PM（下午場）
5. 依取得之 Date, Court 檢查 Excel 檔案是否存在：
   - 若不存在則建立新檔案，並重新讀取 LINE 訊息
6. 表頭 Head：
   ```
   10/9（星期五）歡樂羽球上午場
   ✨地點：晴天羽球館
   費用：270元/人
   時間：9:00-12:00
   ```
7. 名單 Name_List：依順序號 1, 2, 3, …, 候 1, 候 2,.. 讀取名字，並寫入 DataFrame 中
8. 表尾 Tail：
   ```
   🌟限制（xx 人），候補可報名，但要候補到才可來打喔！
   🌟新人請看記事本
   🌟到場繳費簽名時，請在簿子簽上您的號碼跟名字（務必跟群組報名一致，以利對帳）
   ```
9. 將上述 Head, Name_List, Tail 貼到新建立的 Excel 上，並重新存檔（依檔案命名規則）
10. 若不是新開場次則開啟對應的 Excel 檔案，並將 Name_List 貼到對應儲存格，A5=1, A6=2, …；B5=名字 1, B6=名字 2, …

### 1.2 自動功能：報名/取消報名

**觸發條件**：成員發送報名訊息（格式：`日期 Court 名字 +/-N`）

**系統行為**：
1. 讀取 LINE 訊息，並剖析成：
   - 日期 Date（ex. 10/9）
   - 場次 Court（ex. AM/PM）
   - 名字 Name（ex. Beryl）
   - 增減數 Num（ex. +1 or -1）
2. 若無法滿足上述訊息剖析條件，則視為一般聊天訊息，不做處理
3. 若滿足上述訊息剖析條件，則檢查 `YYYY_M_D_Court.xlsx` 是否存在
4. **若檔案存在，且 Num > 0（報名）**：
   - 開啟 Excel 檔，並讀取 Head, Name_List, Tail
   - 檢查 1~max number（ex. 24），對應的 Name 欄位是否為空白
   - 若有空白，則將 Name 依 Num 數量填入空白欄位
   - 若 1~max number 的空白欄位數量 p < Num，則：
     - 先填滿正取空白欄位
     - 多餘的 Num-p 筆資料，自動在 DataFrame 後方 append 新增 候 1, 候 2... 等候補資料
   - 將 Name_List 內容貼至 Excel，並儲存 Excel 檔
   - 將 `Head\n + Name_List\n + Tail` 貼在 LINE 上
5. **若檔案存在，且 Num < 0（取消報名）**：
   - 開啟 Excel 檔，並讀取 Head, Name_List, Tail
   - 檢查 1~max number 及候 1~候 n，對應的 Name 欄位中是否有相符名字
   - 計算相符合的名字數量 = x
   - 若 x < ABS(Num)，則在 LINE 貼文：
     ```
     {Date}+空格+{Court}場中，{Name}報名數=x，< 你要取消的筆數{Num}，本次報名動作無法完成！
     ```
   - 若 x >= ABS(Num)，則：
     - 優先刪除 Name_List 中候補名單（ex. No=候 1, 候 2,..）
     - 再刪除正常名單（ex. No=1, 2, …）
     - 重複上述動作，直到刪除數量=ABS(Num)
     - 將更新後的 Name_List 貼於 Excel 檔案上，並儲存檔案
   - 將 `Head\n + Name_List\n + Tail\n` 貼於 LINE 群組上

---

## 2. 系統架構

### 2.1 系統整體架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────┐
│                     LINE Group (400 users)                  │
└─────────────────────────────┬───────────────────────────────┘
                              │ Webhook
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Gateway Layer (LINE Messaging API)             │
│  • 接收 Webhook POST request                                │
│  • 驗證 X-Line-Signature 簽章                               │
│  • 過濾訊息類型（僅處理 TextMessage）                        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Web Server (FastAPI/Flask)                      │
│  • 路由分流（手動公告 vs 自動報名）                          │
│  • 請求驗證與權限檢查                                       │
│  • 錯誤處理與日誌記錄                                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Business & Parser Layer                            │
│  • Message Parser（訊息剖析器）                              │
│  • Filename Rules Engine（檔名計算引擎）                     │
│  • Registration Engine（報名/取消邏輯引擎）                  │
│  • Duplicate Check（重複報名檢查）                           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Layer (File System)                        │
│  • Excel 檔案儲存（C:\Users\rober\Desktop\LINE群組羽球報名系統\data\ 或 NAS 路徑） │
│  • 檔案鎖（threading.Lock）                                  │
│  • 備份機制（每日自動備份）                                  │
│  • 日誌檔案                                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 各層級分工與詳細運作流程

#### (1) 介面與網關層（Gateway Layer）

**LINE Messaging API 設定**：
- 將系統的官方帳號（Line Bot）加入該 400 人群組
- 在 LINE Developers 後台開啟 Webhook 設定（Use webhook = Enabled）
- 設定 Allow bot to join group chats 權限
- 每當成員在群組傳送訊息，LINE 伺服器會立即向 Webhook URL 發送 HTTP POST 請求

**安全認證**：
- 使用 X-Line-Signature 驗證請求來源
- Channel Access Token 存放於環境變數 `LINE_CHANNEL_ACCESS_TOKEN`
- Channel Secret 存放於環境變數 `LINE_CHANNEL_SECRET`

#### (2) 後端 API 服務層（Web Server）

**技術選型**：Python FastAPI（推薦）或 Flask

**主要職責**：
- 驗證安全簽章：透過 LINE 提供的 X-Line-Signature 驗證請求來源
- 過濾與分流：僅處理 TextMessage（文字訊息），其餘圖片、貼圖、語音直接丟棄
- 錯誤處理：捕獲異常並記錄日誌，返回適當 HTTP 狀態碼
- 健康檢查端點：`GET /health` 提供系統狀態監控

#### (3) 業務邏輯與剖析層（Business & Parser Layer）

**訊息剖析器（Message Parser）**：

| 功能類型 | 解析規則 | 處理邏輯 |
|----------|----------|----------|
| 手動功能（新場次公告） | Date, Court, Site, Time, Name_List | 要素不完整則觸發過濾機制 |
| 自動功能（報名） | Date, Court, Name, Num (+N/-N) | 格式錯誤則忽略 |
| 自動功能（取消） | Date, Court, Name, Num (-N) | 格式錯誤則忽略 |

**檔名計算引擎（Filename Rules Engine）**：
- 計算當前日期與目標月份日期的關係
- 取得系統當前日期 $Today$（以 $Year_{today}, Mon_{today}, Day_{today}$ 表示）
- 比較邏輯：若目標日期 $TargetDate(Year_{today}, Mon, Day) < Today$，代表已跨至下一年，檔案年份改為 $Year_{today} + 1$，否則使用 $Year_{today}$
- 將場次正規化為 AM 或 PM
- 產出標準檔名：`YYYY_Mon_Day-Court.xlsx`

**名單計算與異動引擎（Registration Engine）**：

| 情境 | 邏輯說明 |
|------|----------|
| Num > 0（報名） | 優先搜尋 1~24 欄位的空值，依序補入姓名；若空白數量 p < Num，多餘者自動 append 候補名單 |
| Num < 0（取消） | 檢索名單中目標 Name 出現次數 x；若 x < \|Num\| 則退件；否則優先刪除候補，再刪除正取 |
| 重複報名檢查 | 同一人已在正取名單中，再次報名 +1 時發出警告訊息 |

**容量配置**：
- 預設容量上限：24 人
- 可透過環境變數 `MAX_CAPACITY` 動態調整（預設 24）

#### (4) 資料與檔案持久層（Data Layer）

**檔案儲存位置**：
- 主路徑：`C:\Users\rober\Desktop\LINE群組羽球報名系統\data\`（Windows）或 `/data/badminton/`（Linux/NAS）
- 備份路徑：`C:\Users\rober\Desktop\LINE群組羽球報名系統\data\backup\` 或 `/data/badminton/backup\`
- 每日 00:00 自動備份前一日的 Excel 檔案

**關鍵併發控制**：
- 使用 `threading.Lock()` 實現檔案鎖
- 任何寫入/讀取 Excel 的操作必須取得鎖定後才能執行
- 處理完畢存檔後釋放鎖，確保寫入動作嚴格序列化

**日誌系統**：
- 運行日誌：`logs/app.log`（JSON 格式，便於解析）
- 錯誤日誌：`logs/error.log`
- 日誌輪轉：每日切割，保留最近 30 天
- 記錄內容：時間戳、使用者 ID、訊息內容、處理結果、錯誤訊息

---

## 3. LineBot 建立（手動）

> 本章節說明如何將 LINE Bot 加入群組，基於 LINE 官方文件規定。

### 3.1 前置設定

在將 Bot 加入群組之前，必須先在 LINE Developers Console 完成以下設定：

1. 進入 [LINE Developers Console](https://developers.line.biz/console/)
2. 選擇或建立你的 Channel
3. 在 **Channel settings** 頁面，找到 **Bot settings** 區段
4. 開啟 **Allow bot to join group chats** 選項（預設為關閉）

> ⚠️ **重要限制**：同一時間，一個群組只能加入一個 LINE Official Account（Bot）。

### 3.2 加入群組方法

根據 LINE 官方文件規定，**目前沒有提供 API 自動邀請 Bot 入群組的功能**。必須透過以下手動方式：

| 方法 | 操作步驟 |
|------|----------|
| **方法 A：使用者手動邀請** | 1. 開啟目標群組<br>2. 點擊群組資訊 > 新增成員<br>3. 搜尋 Bot 的名稱（如「@yourbot」）<br>4. 確認加入 |
| **方法 B：透過 LINE Manager** | 使用 [LINE Official Account Manager](https://manager.line.biz/) 管理群組與 Bot 的關聯 |

**具體步驟（方法 A）**：
1. 開啟你的 LINE 應用程式
2. 進入目標群組（例如：400 人的羽球群組）
3. 点击右上角群組資訊
4. 點擊「新增成員」
5. 在搜尋框輸入 Bot 的名稱（例如：`@羽球團報名小幫手`）
6. 點擊 Bot 帳號
7. 確認加入

### 3.3 相關 API

Bot 加入群組後，可使用以下群組相關 API：

| API | 用途 |
|-----|------|
| `GET /bot/group/{groupId}/members` | 獲取群組成員 ID 列表 |
| `GET /bot/group/{groupId}/summary` | 獲取群組摘要（名稱、圖標等） |
| `GET /bot/group/{groupId}/member/{userId}` | 獲取特定成員資料 |
| `POST /bot/broadcast` | 發送訊息給所有成員（廣播） |
| `POST /bot/push` | 發送推送訊息（需指定 groupId） |

### 3.4 Webhook 事件

Bot 加入群組後，可接收以下 webhook 事件：

| 事件類型 | 觸發時機 |
|----------|----------|
| `joined` | Bot 成功加入群組時 |
| `left` | Bot 被移出群組時 |
| `message` | 群組成員發送訊息時 |

### 3.5 群組大小限制

- **LINE 群組上限**：500 人
- **您的群組**：約 400 人
- **狀態**：✅ 在限制範圍內，但建議留意群組成長情況

---

## 4. 安全與權限管理

### 4.1 憑證管理

| 憑證名稱 | 存放方式 | 說明 |
|----------|----------|------|
| LINE Channel Access Token | 環境變數 `LINE_CHANNEL_ACCESS_TOKEN` | 用於呼叫 LINE API |
| LINE Channel Secret | 環境變數 `LINE_CHANNEL_SECRET` | 用於驗證 Webhook 簽章 |
| Telegram Bot Token | 環境變數 `TELEGRAM_BOT_TOKEN` | 用於發送錯誤告警（可選） |
| Telegram Chat ID | 環境變數 `TELEGRAM_CHAT_ID` | 告警接收者 ID |

**注意事項**：
- 敏感憑證不得提交至版本控制系統
- 使用 `.env` 檔案配合 `python-dotenv` 載入
- 定期更換 Token（建議每 90 天）

### 4.2 權限控制

- 僅限群組成員可發送報名/取消訊息
- Bot 不處理非群組訊息（Direct Message 忽略）
- 管理者可透過特定指令（如 `!admin reset`）執行管理操作

---

## 5. 錯誤處理與重試機制

### 5.1 錯誤分類與處理

| 錯誤類型 | 處理方式 | 通知機制 |
|----------|----------|----------|
| LINE API 限流 | 指數退避重試（最多 3 次） | 記錄日誌 |
| Excel 檔案鎖衝突 | 輪詢等待（最多 10 秒） | 記錄日誌 |
| 網路連線失敗 | 重試 3 次後記錄錯誤 | 發送告警 |
| 訊息格式錯誤 | 忽略並記錄 | 無 |
| 資料庫連線失敗 | 重試 3 次後記錄錯誤 | 發送告警 |

### 5.2 監控告警

- **健康檢查端點**：`GET /health` 返回系統狀態（JSON）
- **異常告警**：連續 3 次錯誤後發送 Telegram 通知
- **每日報告**：每日 09:00 發送前一天運作摘要

---

## 6. 部署環境

### 6.1 系統需求

| 項目 | 規格 |
|------|------|
| 作業系統 | Windows 10/11 或 Ubuntu 20.04+ |
| Python 版本 | 3.10+ |
| 記憶體 | 最少 2GB RAM |
| 儲存空間 | 最少 1GB 可用空間 |
| 網路 | 需可存取 LINE Messaging API |

### 6.2 依賴套件

```
fastapi>=0.100.0
uvicorn>=0.23.0
line-bot-sdk>=2.1.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
structlog>=23.0.0
httpx>=0.24.0
```

### 6.3 部署架構

**選項 A：本地運行（推薦初期）**
- 運行於使用者電腦（WSL 或 Windows）
- 使用 systemd/schtasks 保持後台運行
- 適合小規模測試階段

**選項 B：雲端部署**
- 部署於 VPS（如 DigitalOcean、AWS EC2）
- 使用 Docker 容器化管理
- 適合正式上線階段

---

## 7. 測試策略

### 7.1 單元測試

- 訊息剖析器測試（正則表達式匹配）
- 檔名計算引擎測試（邊界條件）
- 報名/取消邏輯測試（正常/異常情境）
- 重複報名檢測測試

### 7.2 整合測試

- LINE Webhook 接收測試
- Excel 檔案讀寫測試
- 併發寫入測試（多使用者同時報名）

### 7.3 測試命令

```bash
# 執行所有測試
pytest tests/ -v

# 執行 coverage 報告
pytest tests/ --cov=app --cov-report=html
```

---

## 8. 維運手冊

### 8.1 啟動腳本

**Windows（PowerShell）**：
```powershell
# 啟動服務
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 或使用 Windows 工作排程器設定開機自動啟動
```

**Linux（systemd）**：
```bash
# 啟動服務
sudo systemctl start badminton-bot.service

# 查看狀態
sudo systemctl status badminton-bot.service

# 查看日誌
sudo journalctl -u badminton-bot.service -f
```

### 8.2 常見問題排除

| 問題 | 可能原因 | 解決方法 |
|------|----------|----------|
| Bot 未回應訊息 | Webhook URL 未設定 | 檢查 LINE Developers 後台設定 |
| 簽章驗證失敗 | Channel Secret 錯誤 | 確認環境變數設定正確 |
| Excel 檔案鎖住 | 上一次執行未正常結束 | 檢查並結束殘留進程 |
| 訊息格式錯誤 | 使用者輸入格式不符 | 檢查日誌確認解析失敗原因 |

### 8.3 備份策略

- **每日備份**：00:00 自動備份前一日所有 Excel 檔案
- **保留週期**：保留最近 90 天的備份
- **備份驗證**：每月隨機抽取備份檔案驗證完整性

---

## 9. 偵錯記錄與已知坑點 ⭐ 新增

本章節記錄實戰中遇到的問題與解決方案，供後續開發者參考。

### 9.1 Webhook Handler 註冊錯誤（嚴重）

**問題現象**：
- LINE 伺服器確實發送請求（ngrok 日誌顯示 200 OK）
- 但系統日誌沒有「收到訊息」記錄
- 只看到「收到無 signature 的請求」或「無效的簽章」錯誤

**根本原因**：
```python
# ❌ 錯誤寫法（原 v11 版本）
webhook_handler.add(MessageEvent, create_handler())

# ✅ 正確寫法（v12 修復）
@webhook_handler.add(MessageEvent)
def handle_message_event(event):
    # handler logic here
```

**說明**：
- `WebhookHandler.add()` 是一個 **decorator 方法**，不是普通方法
- 錯誤調用會返回 None，不會註冊任何 handler
- 正確用法是用 `@` 語法糖裝飾函數

**影響範圍**：所有 LINE 訊息都會被忽略，系統看起來「不工作」

### 9.2 ngrok 認證要求（重要）

**問題現象**：
```
ERROR: authentication failed: This ngrok session is not authenticated.
ERROR: Sign up for an account: https://dashboard.ngrok.com/signup
```

**根本原因**：
- ngrok 自 2024 年 10 月起，免費方案也需要註冊帳號
- 需要 Authtoken 才能建立隧道

**解決方案**：
```bash
# 1. 註冊帳號並取得 Authtoken
# 前往 https://dashboard.ngrok.com/signup

# 2. 配置 authtoken
~/bin/ngrok config add-authtoken <YOUR_TOKEN>

# 3. 啟動隧道
~/bin/ngrok http 8000 --domain=<your-domain>.ngrok-free.app
```

**替代方案**：使用 cloudflared（不需帳號）
```bash
cloudflared tunnel --url http://localhost:8000
```

### 9.3 uvicorn reload 導致服務中斷

**問題現象**：
- 修改 Python 檔案後，uvicorn 自動 reload
- reload 期間服務不可用（502 Bad Gateway）
- LINE 請求在 reload 期間失敗

**解決方案**：
- 生產環境不使用 `--reload` 參數
- 修改代碼後手動重啟服務
- 使用 process manager（如 systemd、supervisor）管理服務

```bash
# 生產環境啟動方式
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 不使用 --reload
```

### 9.4 Python 虛擬環境路徑

**問題現象**：
- 啟動 uvicorn 時找不到模組
- `No module named 'uvicorn'`

**根本原因**：
- WSL 環境使用特定的 Python venv
- 路徑：`/home/robert/.hermes/hermes-agent/venv/`

**解決方案**：
```bash
# 使用正確的 Python 解釋器
/home/robert/.hermes/hermes-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 9.5 簽章驗證失敗排查

**問題現象**：
- LINE 發送請求，但返回 400 Bad Request
- 日誌顯示「無效的簽章」

**排查步驟**：
1. 確認 `.env` 中的 `LINE_CHANNEL_SECRET` 與 LINE Console 一致
2. 確認請求包含 `X-Line-Signature` header
3. 檢查 payload 是否被修改（編碼、換行等）

**測試簽章計算**：
```python
import hmac
import hashlib
import base64

channel_secret = "your_channel_secret"
payload = b'{"type":"message",...}'
signature = base64.b64encode(
    hmac.new(channel_secret.encode(), payload, hashlib.sha256).digest()
).decode()
```

### 9.6 診斷工具與方法

**使用 ngrok Web UI 檢查請求**：
```bash
# 查看請求歷史
curl http://localhost:4040/api/requests/http?limit=10

# 查看特定請求詳情
curl http://localhost:4040/api/requests/http/airt_xxxxx
```

**檢查 handler 註冊狀態**：
```python
from app.main import webhook_handler
print(f"Registered handlers: {len(webhook_handler._handlers)}")
```

**監控 uvicorn 日誌**：
```bash
tail -f logs/app.log
tail -f logs/error.log
```

---

## 10. 附錄

### 10.1 訊息格式範例

**【附 1】手動公告範例**：
```
10/9（星期五）歡樂羽球上午場🏸
✨地點：晴天羽球館
費用：270元/人
時間：9:00-12:00
1. 進
2. 黃保輝
3. 浩雅
4. 慶
...
後補：1.
🌟限制（24 人），候補可報名，但要候補到才可來打喔！
🌟新人請看記事本
🌟到場繳費簽名時，請在簿子簽上您的號碼跟名字（務必跟群組報名一致，以利對帳）
```

**【附 2】自動報名範例**：
```
10/9 AM Beryl +1
10/9 PM Mike -1
```

### 10.2 Excel 檔案結構

| 欄位 | 位置 | 說明 |
|------|------|------|
| Head | A1:A4 | 場次標題資訊 |
| No. | A5:A28 | 序号（1-24）或候補（候 1-候 n） |
| Name | B5:B28 | 姓名 |
| Tail | A30:A33 | 注意事項 |

### 10.3 變更記錄

| 版本 | 日期 | 變更內容 | 作者 |
|------|------|----------|------|
| v0 | 2026-10-09 | 初始版本 | Robert |
| v1 | 2026-10-10 | 補充安全認證、錯誤處理、日誌監控、部署維運等缺失 | Agnes |
| v11 | 2026-10-16 | 新增「LineBot 建立（手動）」章節，補充官方文件規定的加入群組方法 | Agnes |
| v12 | 2026-10-21 | 新增第 9 章「偵錯記錄與已知坑點」，記錄 ngrok 認證、handler 註冊錯誤、uvicorn reload 等實戰問題 | Agnes |

---

**文档結束**
