# LINE Webhook 簽名驗證與 Handler 註冊問題修復記錄

**日期**：2026-10-22  
**問題**：LINE webhook URL verify = error，貼文後 bot 無反應，未生成 Excel 檔案

---

## 根本原因分析

### 1. 簽名驗證失敗

**現象**：
- uvicorn 日誌顯示：`簽名匹配: False`
- body 長度不匹配：收到的 322 bytes vs 預期的 328 bytes
- LINE Console 顯示：`webhook URL verify = error`

**原因**：
FastAPI 的 `request.body()` 會自動解碼 Unicode 轉義序列：
- LINE 發送：`{"text":"\u6e2c\u8a66"}` (328 bytes，包含 Unicode 轉義)
- FastAPI 解碼後：`{"text":"測試"}` (322 bytes，UTF-8 編碼)
- 簽名計算基於不同的 bytes，導致驗證失敗

**解決方案**：
```python
# ❌ 錯誤：使用 request.body()
body = await request.body()  # 返回解碼後的 bytes

# ✅ 正確：使用 request.stream()
body = b''
async for chunk in request.stream():
    body += chunk  # 返回原始 bytes，保留 Unicode 轉義
```

### 2. Webhook Handler 未註冊

**現象**：
- 日誌顯示：`INFO:linebot:No handler of MessageEvent and no default handler`
- 請求成功返回 200，但未處理事件

**原因**：
uvicorn 的 `--reload` 模式會啟動兩個進程：
- 監控進程：執行 lifespan（初始化服務、註冊 handler）
- Worker 進程：處理 HTTP 請求

當程式碼修改並重新載入時，lifespan 可能在監控進程中執行，但請求由 worker 進程處理，導致 handler 未註冊。

**解決方案**：
```python
# 在 webhook 函數中添加安全檢查
if not hasattr(app.state, 'webhook_handler') or not app.state.webhook_handler._handlers:
    from linebot.models import MessageEvent
    if not hasattr(app.state, 'webhook_handler'):
        from linebot import WebhookHandler
        app.state.webhook_handler = WebhookHandler(LINE_CHANNEL_SECRET)
    app.state.webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
```

### 3. .env 檔案位置錯誤

**現象**：
- `LINE_CHANNEL_SECRET` 讀取到預設值 `*** 請替換為你的 Secret ***`
- 簽名驗證失敗

**原因**：
- uvicorn 工作目錄：`/home/robert/workspace/LINE群組羽球報名系統/`
- `.env` 檔案位置：`/mnt/c/Users/rober/Desktop/LINE群組羽球報名系統/.env`
- Python 的 `python-dotenv` 只從當前工作目錄讀取 `.env`

**解決方案**：
```bash
cp /mnt/c/Users/rober/Desktop/LINE群組羽球報名系統/.env \
   /home/robert/workspace/LINE群組羽球報名系統/.env
```

### 4. LINE SDK 的 `add()` 方法使用錯誤

**現象**：
- handler 數量為 0
- 日誌顯示：`No handler of MessageEvent and no default handler`

**原因**：
LINE SDK 的 `WebhookHandler.add()` 是一個裝飾器，需要使用 `@` 語法：
```python
# ❌ 錯誤：直接調用
webhook_handler.add(MessageEvent, create_handler())

# ✅ 正確：使用 decorator 語法
@webhook_handler.add(MessageEvent)
def handle_message_event(event):
    ...

# 或直接使用內部方法
webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
```

---

## 修復後的完整代碼

### `app/main.py` - webhook 路由
```python
@app.post("/webhook/line")
async def webhook(request: Request):
    """LINE Webhook 端點"""
    from app.config import LINE_CHANNEL_SECRET
    from linebot.exceptions import InvalidSignatureError
    from linebot.models import MessageEvent
    
    signature = request.headers.get('X-Line-Signature')
    
    if not signature:
        logger.warning("收到無 signature 的請求 (可能是測試)")
        return {"status": "ok", "note": "no signature (test request)"}
    
    # 讀取原始 body（不使用 FastAPI 的自動解析）
    body = b''
    async for chunk in request.stream():
        body += chunk
    
    logger.info(f"收到請求: body長度={len(body)}, signature前20字元={signature[:20]}")
    
    try:
        # 檢查簽名是否匹配（使用原始 body bytes）
        generated_sig = base64.b64encode(
            hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
        ).decode()
        
        logger.info(f"期望簽名: {generated_sig[:20]}...")
        logger.info(f"收到簽名: {signature[:20]}...")
        logger.info(f"簽名匹配: {compare_digest(generated_sig.encode(), signature.encode())}")
        
        if not compare_digest(generated_sig.encode(), signature.encode()):
            logger.error(f"簽名不匹配！")
            raise InvalidSignatureError(f"Invalid signature. signature={signature}")
        
        # 確保 handler 已註冊（--reload 模式下 lifespan 可能未執行）
        if not hasattr(app.state, 'webhook_handler') or not app.state.webhook_handler._handlers:
            if not hasattr(app.state, 'webhook_handler'):
                from linebot import WebhookHandler
                app.state.webhook_handler = WebhookHandler(LINE_CHANNEL_SECRET)
            app.state.webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
        
        # 簽名驗證通過，調用 webhook handler 處理事件
        body_str = body.decode('utf-8')
        app.state.webhook_handler.handle(body_str, signature)
        
        return {"status": "ok"}
        
    except InvalidSignatureError:
        if app.state.log_service:
            app.state.log_service.error("無效的簽章")
        raise HTTPException(status_code=400)
```

---

## 驗證結果

### 測試步驟
1. 複製 `.env` 到工作目錄
2. 重新啟動 uvicorn
3. 發送測試請求
4. 檢查日誌

### 預期結果
```
INFO:app.main:簽名匹配: True
INFO:app.main:收到訊息: 10/25（星期日）歡樂羽球下午場...
INFO:app:{"message": "處理成功", "source_id": "...", "action": "created"}
INFO:127.0.0.1:... - "POST /webhook/line HTTP/1.1" 200 OK
```

### 實際結果
```
✅ 簽名驗證成功
✅ 訊息處理成功
✅ Excel 檔案生成：data/2026_10_25-PM.xlsx
✅ LINE 回覆成功
```

---

## 關鍵要點總結

1. **簽名驗證**：使用 `request.stream()` 而非 `request.body()` 獲取原始 bytes
2. **Handler 註冊**：在 webhook 函數中添加安全檢查，確保 handler 已註冊
3. **.env 位置**：必須複製到 uvicorn 工作目錄
4. **LINE SDK**：使用 `_WebhookHandler__add_handler()` 而非 `add()`

---

**相關檔案**：
- `app/main.py` - 主程式（已修復）
- `app/config.py` - 配置模組
- `.env` - 環境變數
- `logs/app.log` - 應用日誌
- `20261022_debug.md` - Debug 記錄