# LINE 群組羽球報名系統

自動處理 LINE 群組羽球活動報名的 Bot 系統。

## 功能

### 手動功能：新場次公告
在 LINE 群組發布羽球訊息（附公告格式），系統會：
1. 解析日期、場次、場地、時間、名單
2. 檢查是否為新場次
3. 建立新的 Excel 報名表
4. 回覆更新後的名單

### 自動功能：報名/取消報名
成員發送格式：`日期 Court 名字 +/-N`
- `10/24 PM Robert +1` - 報名
- `10/24 PM Robert -1` - 取消報名

系統會：
1. 解析報名資訊
2. 更新 Excel 檔案
3. 回覆更新後的名單

## 安裝

```bash
cd /home/robert/workspace/LINE群組羽球報名系統
pip install -r requirements.txt
```

## 設定

複製 `.env.example` 並填入 LINE Bot 憑證：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：
```
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_CHANNEL_SECRET=your_secret_here
MAX_CAPACITY=24
```

## 啟動

```bash
# 開發模式（熱重載）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 makefile
make run
```

## 測試

```bash
# 執行所有測試
pytest tests/ -v

# 執行特定測試
pytest tests/test_parser.py -v
```

## 部署

1. 使用 cloudflared 建立公開 URL
2. 將 webhook URL 設定到 LINE Developers Console
3. 確保 Bot 已加入目標群組

## 檔案結構

```
LINE群組羽球報名系統/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 主應用程式
│   ├── config.py            # 配置管理
│   ├── parsers/
│   │   └── message_parser.py  # 訊息剖析器
│   ├── engines/
│   │   ├── filename_engine.py  # 檔名計算引擎
│   │   └── registration_engine.py  # 報名引擎
│   ├── services/
│   │   ├── excel_service.py    # Excel 檔案服務
│   │   └── log_service.py      # 日誌服務
│   └── models/
│       └── registration.py     # 數據模型
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_filename_engine.py
│   └── test_registration_engine.py
├── logs/                    # 日誌目錄
├── .env.example            # 環境變數範本
├── requirements.txt        # 依賴套件
├── Makefile               # 建置指令
└── README.md
```

## 技術選型

- **Web Framework**: FastAPI
- **LINE SDK**: line-bot-sdk
- **Excel 處理**: pandas + openpyxl
- **環境變數**: python-dotenv
- **伺服器**: uvicorn

## 注意事項

- Excel 檔案儲存於 `C:\Users\rober\Desktop\LINE群組羽球報名系統\Data\`
- 每日 00:00 自動備份前一日的 Excel 檔案
- 使用 `threading.Lock()` 確保併發安全
