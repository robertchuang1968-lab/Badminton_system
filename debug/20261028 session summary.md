# LINE 群組羽球報名系統 - Session 修改記錄

**日期：2026-10-28 ~ 2026-10-29**

---

## 一、本次修改重點

### 1. 過期場次檢查邏輯
**檔案**：`app/parsers/message_parser.py`
- 新增 `_calculate_expiry(date_str)` 方法
- 在 `parse_registration()`、`parse_registration_batch()`、`parse_batch_operation()` 中呼叫
- 跨年份邊界處理：若月份 < 當前月份，年份 +1

### 2. 名額已滿時轉候補邏輯
**檔案**：`app/engines/registration_engine.py`
- 移除 `_handle_signup()` 的「名額已滿」拒絕邏輯
- 當 `available_spots = 0` 時，直接進入候補邏輯

### 3. 候補名單顯示原始名字
**檔案**：`app/engines/registration_engine.py`
- 候補新增邏輯改為顯示原始名字而非「候1」
- 候補顯示邏輯改為顯示所有候補（不限於「候」開頭）

### 4. Excel 鎖定錯誤處理
**檔案**：`app/services/excel_service.py`
- 新增空檔案檢查（第 203-205 行）
- 新增格式錯誤捕獲（第 207-213 行）
- 刪除多餘重複的 `pd.read_excel()` 呼叫（原第 119 行）

### 5. AM/PM 大小寫不敏感
**檔案**：`app/parsers/message_parser.py`
- 使用 `(?i:AM|PM)` 讓 AM/PM 不區分大小寫

---

## 二、修改結果

| 功能 | 狀態 | 備註 |
|------|------|------|
| 過期檢查 | ✅ 完成 | 10/25 等過期場次會返回「已過期」 |
| 名額已滿轉候補 | ✅ 完成 | 名額滿時自動加入候補名單 |
| 候補顯示名字 | ✅ 完成 | 候補顯示原始名字而非「候1」 |
| Excel 鎖定處理 | ⚠️ 部分完成 | WSL 環境下鎖定檢測不可靠（見下方說明） |
| AM/PM 不敏感 | ✅ 完成 | am/pm/AM/PM 皆可辨識 |
| 空檔案檢查 | ✅ 完成 | 空 Excel 檔案會返回友好錯誤訊息 |

---

## 三、重要發現：WSL 環境檔案鎖定行為

### 問題描述
在 WSL (Windows Subsystem for Linux) 環境下，Python **不會**遵守 Windows Excel 的檔案鎖定機制。

### 實際案例（2026-10-29）
- `2026_10_29-PM.xlsx` 存在 `~$2026_10_29-PM.xlsx` 鎖定檔（表示 Windows Excel 正在開啟）
- 用戶輸入「10/29 PM Gina +1」報名
- Bot **成功處理**報名並回覆完整名單
- 證明 WSL 下 Python 可繞過 Windows 檔案鎖定

### 風險
- 靜默資料損壞：同時寫入可能導致 Excel 內容錯亂
- 鎖定檢測不可靠：檢測 `~$` 鎖定檔不代表檔案真的被鎖定
- `PermissionError` 幾乎不會觸發

### 建議處理方式
1. 避免同時操作：確保 Windows Excel 關閉後再由 Bot 運作
2. 或改用網路共享：將 Excel 放在網路共用位置
3. 記錄警告而非阻擋：若檢測到鎖定檔，記錄 warning 但不阻塞報名

詳細記錄請參見：`references/excel-locking-issue-wsl.md`

---

## 四、相關檔案清單

| 檔案 | 說明 |
|------|------|
| `app/parsers/message_parser.py` | 訊息解析器，含過期計算、AM/PM 不敏感 |
| `app/engines/registration_engine.py` | 報名引擎，含候補邏輯 |
| `app/services/excel_service.py` | Excel 讀寫服務，含空檔案檢查 |
| `app/main.py` | FastAPI 主程式，webhook handler |
| `app/models/registration.py` | 資料模型，含 `full_date` 和 `is_expired` |

---

## 五、重要提醒

1. **uvicorn 已使用 `--reload` 模式**，修改程式碼後自動重啟
2. **ngrok tunnel**：`https://platypus-flexible-buck.ngrok-free.app -> localhost:8000`
3. **Excel 路徑**：`/home/robert/workspace/LINE群組羽球報名系統/Data/`
4. **WSL 環境注意**：Python 可繞過 Windows 檔案鎖定，需手動協調使用時間

---

*整理時間：2026-10-29*