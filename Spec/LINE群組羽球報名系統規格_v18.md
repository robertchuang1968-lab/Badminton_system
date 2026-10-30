# LINE 群組羽球報名系統規格 v18

> 版本日期：2026-10-22
> 原始版本：LINE 群組羽球報名系統規格（v17）
> 變更說明：新增「踩坑記錄與已修復問題」章節；修正 LINE SDK 的 `add()` 方法用法；修正 `uvicorn --reload` 模式下的 lifespan 問題；Tail 解析改為關鍵字驅動（「限制...人」），忽略前綴符號；修正 LINE_CHANNEL_SECRET 載入問題

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

**觸發條件**：成員發送報名訊息（格式：`日期 Court 名字 +/-N` 或 `本次操作報名：名字 +/-N`）

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
   - **檢查 1~MAX_CAPACITY**，對應的 Name 欄位是否為空白
   - 若有空白，則將 Name 依 Num 數量填入空白欄位
   - 若 1~MAX_CAPACITY 的空白欄位數量 p < Num，則：
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
     - **優先刪除 Name_List 中候補名單**（ex. No=候 1, 候 2,..）
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
│  • Excel 檔案儲存（C:\SuperTSC64\user\ 或 NAS 路徑）         │
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

**Webhook URL 設定**：
- 完整 URL：`https://platypus-flexible-buck.ngrok-free.app/webhook/line`
- ngrok tunnel domain：`platypus-flexible-buck.ngrok-free.app`（固定值，禁止修改）
- Webhook 驗證機制：LINE 發送 GET 請求驗證，業務訊息使用 POST 請求

#### (2) 後端 API 服務層（Web Server）

**技術選型**：Python FastAPI（推薦）或 Flask

**主要職責**：
- 驗證安全簽章：透過 LINE 提供的 X-Line-Signature 驗證請求來源
- 過濾與分流：僅處理 TextMessage（文字訊息），其餘圖片、貼圖、語音直接丟棄
- 錯誤處理：捕獲異常並記錄日誌，返回適當 HTTP 狀態碼
- 健康檢查端點：`GET /health` 提供系統狀態監控
- Webhook 路由：
  - `GET /webhook/line`：LINE 驗證請求（返回 200）
  - `POST /webhook/line`：LINE 業務訊息（簽章驗證 + 事件處理）

#### (3) 業務邏輯與剖析層（Business & Parser Layer）

**訊息剖析器（Message Parser）**：

| 功能類型 | 解析規則 | 處理邏輯 |
|----------|----------|----------|
| 手動功能（新場次公告） | Date, Court, Site, Time, Name_List | 要素不完整則觸發過濾機制 |
| 自動功能（報名） | Date, Court, Name, Num (+N/-N) | 格式錯誤則忽略 |
| 自動功能（取消） | Date, Court, Name, Num (-N) | 格式錯誤則忽略 |
| 批量操作 | 本次操作報名：Name1 +/-N1, Name2 +/-N2 | 支援多筆一次性處理 |

**檔名計算引擎（Filename Rules Engine）**：
- 計算當前日期與目標月份日期的關係
- 取得系統當前日期 $Today$（以 $Year_{today}, Mon_{today}, Day_{today}$ 表示）
- 比較邏輯：若目標日期 $TargetDate(Year_{today}, Mon, Day) < Today$，代表已跨至下一年，檔案年份改為 $Year_{today} + 1$，否則使用 $Year_{today}$
- 將場次正規化為 AM 或 PM
- 產出標準檔名：`YYYY_Mon_Day-Court.xlsx`

**名單計算與異動引擎（Registration Engine）**：

| 情境 | 邏輯說明 |
|------|----------|
| Num > 0（報名） | 優先搜尋 1~MAX_CAPACITY 欄位的空值，依序補入姓名；若空白數量 p < Num，多餘者自動 append 候補名單（編號從 MAX_CAPACITY + 1 開始）；【手動】報名允許重複（同一人名可出現多次） |
| Num < 0（取消） | 檢索名單中目標 Name 出現次數 x；若 x < \|Num\| 則退件；否則**優先刪除候補**，再刪除正取 |
| 重複報名檢查 | 【手動】報名不檢查重複，同一人名可多次報名 |
| 批量操作 | 支援「本次操作報名：Name1 +/-N1, Name2 +/-N2」格式，一次性處理多筆報名/取消 |

**容量配置**：
- 每場次容量由 Tail 文字中的「限制（XX人）」自動解析
- 格式：`🌟限制（8人）`、`🌟限制（16人）`、`🌟限制（24人）`、`🌟限制（32人）` 等
- 容量必須為 8 的倍數
- 若 Tail 中無「限制」文字，則使用環境變數 `MAX_CAPACITY` 預設值（24）
- 不同場次可有不同容量（由公告時的 Tail 決定）

**Tail 解析規則**：
- **關鍵字驅動**：只要行中包含「限制」和「人」兩個關鍵詞，即視為 Tail 行
- **忽略前綴符號**：系統會自動忽略任何前綴符號（🌟、🚨、⚠️、※、📌 等），只關注關鍵字
- **多行 Tail**：起始行之後，以特殊符號開頭的連續行也納入 Tail 區塊
- **結束條件**：遇到非特殊符號開頭且不含關鍵詞的行時，Tail 區塊結束

#### (4) 資料與檔案持久層（Data Layer）& 關鍵併發控制

由於 400 人的群組在熱門場次開放時，極易出現多人同時送出 +1 訊息的情況，若直接讓多個 API 線程同時開啟寫入同一個 Excel 檔，會引發 PermissionError (File Lock) 或覆寫蓋掉別人資料的問題。

**解決方案：線程鎖 (Threading Lock) / 佇列 (Queue) 機制**：
- 在 Python 中維護一個全局檔案鎖（例如 `threading.Lock()`）或任務佇列（Queue）
- 任何寫入/讀取 Excel 的操作必須取得鎖定後才能執行，處理完完畢存檔後釋放鎖，確保寫入動作嚴格序列化（Single Thread Processing for I/O）

**日誌系統**：
- 運行日誌：`logs/app.log`（JSON 格式，便於解析）
- 錯誤日誌：`logs/error.log`
- 日誌輪轉：每日切割，保留最近 30 天
- 記錄內容：時間戳、使用者 ID、訊息內容、處理結果、錯誤訊息

---

## 3. LineBot 建立（手動）

### 3.1 前置設定（必須先完成）

在將 Bot 加入群組之前，必須先在 [LINE Developers Console](https://developers.line.biz/console/) 完成以下設定：

| 步驟 | 操作 |
|------|------|
| 1 | 前往 LINE Developers Console，選擇或建立你的 Channel |
| 2 | 進入 **Channel settings** 頁面 |
| 3 | 在 **Bot settings** 區段，開啟 **Allow bot to join group chats** 選項（預設為關閉） |

> ⚠️ **重要限制**：同一時間，一個群組只能加入一個 LINE Official Account（Bot）。

### 3.2 將 Bot 加入群組的方法

根據 LINE 官方文件，**目前沒有提供 API 自動邀請 Bot 入群組的功能**，必須透過以下手動方式：

#### 方法 A：使用者手動邀請

1. 在 LINE 手機應用程式中開啟目標群組
2. 點擊右上角的 **群組資訊**（或新增成員按鈕）
3. 選擇 **新增成員**
4. 搜尋 Bot 的名稱（格式為 `@yourbot` 或顯示為官方帳號）
5. 確認加入

#### 方法 B：透過 LINE Official Account Manager

使用 [LINE Official Account Manager](https://manager.line.biz/) 進行更詳細的群組與 Bot 關聯管理。

### 3.3 加入群組後的相關 API

Bot 成功加入群組後，可使用以下群組相關 API：

| API | 用途 |
|-----|------|
| `GET /bot/group/{groupId}/members` | 獲取群組成員 ID 列表 |
| `GET /bot/group/{groupId}/summary` | 獲取群組摘要（名稱、圖標等） |
| `GET /bot/group/{groupId}/member/{userId}` | 獲取特定成員資料 |
| `POST /bot/broadcast` | 發送訊息給所有成員（廣播） |
| `POST /bot/push` | 發送推送訊息（需指定 groupId） |

### 3.4 Webhook 事件處理

Bot 加入群組後，可接收以下 webhook 事件：

| 事件類型 | 觸發時機 |
|----------|----------|
| `joined` | Bot 成功加入群組時 |
| `left` | Bot 被移出群組時 |
| `message` | 群組成員發送訊息時 |

### 3.5 群組大小限制

| 限制項目 | 說明 |
|----------|------|
| 群組人數上限 | 目前為 500 人 |
| 您的群組規模 | 約 400 人（在限制範圍內） |
| 建議 | 若未來群組成長接近上限，需評估系統負載與 LINE API 效能 |

---

## 4. 安全與權限管理

### 4.1 憑證管理

| 憑證名稱 | 存放方式 | 說明 |
|----------|----------|------|
| LINE Channel Access Token | 環境變數 `LINE_CHANNEL_ACCESS_TOKEN` | 用於呼叫 LINE API |
| LINE Channel Secret | 環境變數 `LINE_CHANNEL_SECRET` | 用於驗證 Webhook 簽章 |
| 資料庫密碼（如有） | 環境變數或 .env 檔案 | 不使用硬編碼 |

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
python-line-bot-sdk>=2.1.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
structlog>=23.0.0
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

# 執行.coverage 報告
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
| `No handler of MessageEvent` | LINE SDK `add()` 方法使用錯誤 | 使用 `_WebhookHandler__add_handler()` 代替 |
| 服務無法啟動 | `--reload` 模式下 lifespan 未執行 | 直接使用 `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

### 8.3 備份策略

- **每日備份**：00:00 自動備份前一日所有 Excel 檔案
- **保留週期**：保留最近 90 天的備份
- **備份驗證**：每月隨機抽取備份檔案驗證完整性

---

## 9. 踩坑記錄與已修復問題

### 9.1 LINE SDK 的 `add()` 方法使用錯誤

**問題現象**：Bot 收到訊息後無反應，日誌顯示 `No handler of MessageEvent and no default handler`。

**根本原因**：
LINE SDK 的 `WebhookHandler.add()` 方法是一個**裝飾器**，需要使用 `@` 語法：
```python
# 錯誤用法（直接調用，不會註冊 handler）
webhook_handler.add(MessageEvent, create_handler())

# 正確用法（使用 @ 裝飾器語法）
@webhook_handler.add(MessageEvent)
def handler(event):
    ...
```

**解決方案**：
使用 LINE SDK 的內部方法 `_WebhookHandler__add_handler()`：
```python
webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
```

**影響範圍**：
- 所有使用 LINE SDK `WebhookHandler` 的專案
- 症狀：簽名驗證成功，但訊息處理函數未被調用

---

### 9.2 uvicorn `--reload` 模式下的 lifespan 問題

**問題現象**：
- 使用 `--reload` 模式啟動 uvicorn
- 簽名驗證成功
- 但 handler 未註冊，訊息未被處理

**根本原因**：
uvicorn 的 `--reload` 模式會啟動兩個進程：
1. **監控進程**：監控檔案變更，執行 lifespan
2. **Worker 進程**：處理 HTTP 請求

當程式碼修改並重新載入時，lifespan 可能在監控進程中執行，但請求由 worker 進程處理。兩者雖共享同一 Python 進程空間，但 lifespan 中的初始化邏輯（如註冊 handler）可能未在 worker 進程中正確執行。

**解決方案**：
1. **直接使用 `--reload` 模式**：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   不要使用 `&` 背景執行，確保進程不被終止。

2. **在 webhook 函數中添加安全檢查**：
   ```python
   # 確保 handler 已註冊
   if not app.state.webhook_handler._handlers:
       app.state.webhook_handler._WebhookHandler__add_handler(
           create_handler(), MessageEvent
       )
   ```

**影響範圍**：
- 所有使用 FastAPI + uvicorn `--reload` 的專案
- 症狀：lifespan 中的初始化代碼未執行，服務狀態不一致

---

### 9.3 Tail 符號兼容性問題

**問題現象**：
- 規格書示例使用 `🌟` 符號
- 用戶實際使用 `🚨` 符號
- 系統無法解析 Tail

**根本原因**：
原 `_extract_tail()` 方法只識別 `🌟` 符號。

**解決方案**：
修改為關鍵字驅動，忽略前綴符號：
```python
def _extract_tail(self, message: str) -> Optional[str]:
    """提取備註尾碼 - 以關鍵字驅動，忽略前綴符號"""
    lines = message.split('\\n')
    tail_lines = []
    in_tail = False

    for line in lines:
        stripped = line.strip()
        # 檢測 Tail 起始行：包含「限制」和「人」關鍵詞
        if '限制' in stripped and '人' in stripped:
            in_tail = True
            tail_lines.append(stripped)
        elif in_tail:
            # 已在 Tail 區塊中，繼續收集後續行
            if stripped.startswith(('🌟', '🚨', '⚠️', '※', '📌')):
                tail_lines.append(stripped)
            else:
                break  # Tail 區塊結束

    return '\\n'.join(tail_lines) if tail_lines else None
```

**核心邏輯**：
1. **關鍵字驅動**：只要行中包含「限制」和「人」，即視為 Tail 起始行
2. **忽略前綴符號**：不依賴任何特定符號（🌟、🚨 等）
3. **區塊收集**：起始行之後，連續的特殊符號開頭行也納入 Tail
4. **容錯性**：即使沒有符號，只要有「限制...人」關鍵詞就能正確解析

**影響範圍**：
- LINE 群組羽球報名系統
- 症狀：Tail 無法解析，容量無法從 Tail 中提取

---

### 9.4 LINE_CHANNEL_SECRET 未正確載入

**問題現象**：
- 簽名驗證失敗
- `.env` 檔案中有正確的 `LINE_CHANNEL_SECRET`

**根本原因**：
`.env` 檔案位置錯誤，uvicorn 工作目錄與 `.env` 檔案不在同一目錄。

**解決方案**：
確保 `.env` 檔案位於 uvicorn 工作目錄中：
```bash
cp /mnt/c/Users/rober/Desktop/LINE群組羽球報名系統/.env \
   /home/robert/workspace/LINE群組羽球報名系統/.env
```

**影響範圍**：
- WSL 環境下運行 Python 服務的專案
- 症狀：環境變數未載入，預設值被使用

---

### 9.5 FastAPI 簽名驗證邏輯錯誤

**問題現象**：
- 簽名驗證失敗
- body 長度正確（328 bytes）
- 但計算出的簽名與收到簽名不匹配

**根本原因**：
LINE 發送的是原始 JSON bytes（包含 Unicode 轉義如 `\u6e2c`），但 FastAPI 的 `request.body()` 可能被中間件修改。

**解決方案**：
使用 `request.stream()` 獲取原始 bytes：
```python
body = b''
async for chunk in request.stream():
    body += chunk
```

**影響範圍**：
- 所有使用 FastAPI 處理 LINE webhook 的專案
- 症狀：簽名驗證失敗，即使 Channel Secret 正確

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
5. 袁
6. mitch6666
7. mitch6666
8. mitch6666
9. mitch6666
10. 何紓柔
11. 何震維
12. 黃帷芩
13. 宜辰
14. Beryl
15. Beryl
16. Beryl
17. 文華
18. 凱
19. 阿瑋
20. 李冠亨
21. TSAl
22. 鈞皓
23. 
24. 

後補：1.
🌟限制（24人），候補可報名，但要候補到才可來打喔！
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
| 正取名單 | A5:A28 | 序号（1-24）與姓名，僅填滿正取名額 |
| 候補名單 | A29+ | 序号（25, 26, ...）與姓名（如「候1」、「候2」） |
| Tail | 候補名單之後 | 注意事項（🌟開頭的文字） |

**重要規則**：
- 每場次容量上限為 `MAX_CAPACITY`（預設 24）人
- 正取名單編號範圍：1 ~ MAX_CAPACITY
- 候補名單編號從 MAX_CAPACITY + 1 開始（如第25位、第26位）
- Tail 文字必須放在所有名單（含候補）之後
- 報名時先填入正取空位，空位用完後才新增候補
- 取消報名時優先刪除候補，再刪除正取

### 10.3 變更記錄

| 版本 | 日期 | 變更內容 | 作者 |
|------|------|----------|------|
| v0 | 2026-10-09 | 初始版本 | Robert |
| v1 | 2026-10-10 | 補充安全認證、錯誤處理、日誌監控、部署維運等缺失 | Agnes |
| v11 | 2026-10-10 | 新增「LineBot 建立（手動）」章節，補充官方文件規定的加入群組方法 | Agnes |
| v12 | 2026-10-21 | 修正候補名單編號規則：候補應放在正取（1-MAX_CAPACITY）之後，編號從 MAX_CAPACITY+1 開始；Tail 文字移至候補之後 | Robert |
| v13 | 2026-10-21 | 容量支援動態解析：從 Tail 文字「限制（XX人）」自動讀取容量，支援 8/16/24/32/...等不同場次規模 | Robert |
| v14 | 2026-10-21 | 新增「本次操作報名」批量操作功能，支援多筆報名/取消一次性處理；手動報名允許重複（同一人名可多次報名） | Robert |
| v15 | 2026-10-21 | 修正取消報名邏輯：優先從候補刪除，再從正取刪除 | Robert |
| v16 | 2026-10-21 | 整合原始規格書內容，補充附件範例，更新變更記錄格式 | Robert |
| v17 | 2026-10-22 | 新增「踩坑記錄與已修復問題」章節；修正 LINE SDK `add()` 方法用法；修正 `uvicorn --reload` 模式問題；Tail 解析改為關鍵字驅動（「限制...人」），忽略前綴符號 | Robert/Agnes |
| v18 | 2026-10-22 | 新增「LINE_CHANNEL_SECRET 未正確載入」與「FastAPI 簽名驗證邏輯錯誤」踩坑記錄；完善維運手冊；Tail 解析改為關鍵字驅動（「限制...人」），忽略前綴符號 | Robert/Agnes |
| v19 | 2026-10-29 | 新增「ngrok 啟動方式說明」與「同一日期多場次處理」；新增啟動腳本 `start_server.sh` 使用方法與測試結果 | Robert/Agnes |

---

## 附錄：ngrok 啟動方式說明

### 正確的 ngrok 啟動方式

```bash
ngrok start line-bot
```

或指定日誌：
```bash
ngrok start line-bot --log=/home/robert/workspace/LINE群組羽球報名系統/logs/ngrok.log
```

### 錯誤命令（會產生隨機域名）

```bash
ngrok http 8000  # 會忽略 ngrok.yml 配置，使用隨機域名
```

### 為什麼要用 `ngrok start line-bot`？

| 命令 | 行為 |
|------|------|
| `ngrok start line-bot` | 讀取 `ngrok.yml` 中的「line-bot」tunnel 配置，使用固定域名 |
| `ngrok http 8000` | 建立命令列暫存 tunnel，使用隨機域名（每次不同） |

### 配置檔案位置

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

### LINE Webhook URL

**固定網址**（不得更改）：
```
https://platypus-flexible-buck.ngrok-free.app/webhook/line
```

### 啟動腳本使用方法

```bash
cd /home/robert/workspace/LINE群組羽球報名系統

./start_server.sh start      # 啟動所有服務
./start_server.sh stop       # 停止所有服務
./start_server.sh status     # 查看狀態
./start_server.sh restart    # 重新啟動
```

**功能說明**：

| 功能 | 說明 |
|------|------|
| 自動檢測現狀 | 若服務已在運行，跳過啟動避免重複 |
| 健康檢查 | 確認 webhook URL 可達 |
| PID 記錄 | 寫入 `logs/pids/` 目錄 |
| 日誌分離 | uvicorn → `logs/uvicorn.log`，ngrok → `logs/ngrok.log` |

**檢測邏輯**：
- uvicorn：`pgrep -f "uvicorn app.main"`
- ngrok：`curl http://localhost:4040/api/tunnels` 確認是否已有固定域名 tunnel

### 測試結果

| 情境 | uvicorn | ngrok | 結果 |
|------|---------|-------|------|
| 兩者都斷線 | ❌ | ❌ | 同時啟動兩個 ✓ |
| 只有 uvicorn 斷線 | ❌ | ✅ | **只重啟 uvicorn** ✓ |
| 只有 ngrok 斷線 | ✅ | ❌ | **只重啟 ngrok** ✓ |
| 兩者都在運行 | ✅ | ✅ | 跳過，顯示現狀 ✓ |

**測試日期**：2026-10-29
**測試方法**：
1. 手動 kill uvicorn → 執行 `./start_server.sh start` → 確認只重啟 uvicorn
2. 手動 kill ngrok → 執行 `./start_server.sh start` → 確認只重啟 ngrok

### 同一日期多場次處理

若同一日期有多個場次（上午 + 下午），會產生兩個 Excel 檔案：
- `2026_10_31-AM.xlsx` → 上午場
- `2026_10_31-PM.xlsx` → 下午場

**注意**：若先貼下午場公告再貼上午場公告，會同時存在兩個檔案。建議刪除錯誤的檔案。

### 日誌檔案路徑

- uvicorn log: `logs/uvicorn.log`
- ngrok log: `logs/ngrok.log`
- PID 記錄: `logs/pids/`

---

**文档結束**
