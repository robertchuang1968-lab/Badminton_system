"""
LINE 群組羽球報名系統 - FastAPI 主應用程式
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceGroup
)

from app.config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    MAX_CAPACITY,
    EXCEL_BASE_PATH,
    LOG_DIR
)
from app.parsers.message_parser import MessageParser
from app.engines.filename_engine import FilenameEngine
from app.services.excel_service import ExcelService
from app.services.log_service import LogService
from app.services.permission_service import PermissionService
from app.engines.registration_engine import RegistrationEngine

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全域變量（用於 handler 存取）
_services = {}


# 全域 webhook handler
webhook_handler = WebhookHandler(LINE_CHANNEL_SECRET)


def create_handler():
    """建立訊息處理器"""
    
    def handler(event):
        if not isinstance(event, MessageEvent):
            return

        if not isinstance(event.message, TextMessage):
            return

        message_text = event.message.text
        source = event.source

        # 僅處理群組訊息
        if not isinstance(source, SourceGroup):
            return

        source_id = source.group_id
        user_id = source.user_id

        # 從全域變量取得服務
        log_service = _services.get('log_service')
        parser = _services.get('parser')
        registration_engine = _services.get('registration_engine')
        line_bot_api = _services.get('line_bot_api')
        permission_service = _services.get('permission_service')
        excel_service = _services.get('excel_service')
        
        # /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        # 2026/10/30 新增程式碼
        # 處理 /get_group_id 指令（不需要權限）
        if message_text.strip() == '/get_group_id':
            # 組建回覆訊息
            json_example = '{\n  "managers": [\n    "' + user_id + '"\n  ]\n}'
            reply_text = f"📋 你的管理員資料：\n\n群組 ID：{source_id}\n你的 User ID：{user_id}\n\n請將此 User ID 新增至 app/data/admin_list.json\n{json_example}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            log_service.info(
                "收到 /get_group_id 指令",
                source_id=source_id,
                user_id=user_id
            )
            return
        
        # 檢查管理指令權限
        if message_text.strip().startswith('/') and permission_service:
            if not permission_service.is_manager(user_id):
                reply_text = "❌ 無權執行此指令，僅管理人可用"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                log_service.warning(
                    "無權執行指令",
                    source_id=source_id,
                    user_id=user_id,
                    command=message_text.strip()
                )
                return
        
        # /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        # 處理 /capacity 指令
        if message_text.strip().startswith('/capacity'):
            capacity_data = parser.parse_capacity_command(message_text)
            if not capacity_data:
                # 指令格式錯誤或參數不足
                reply_text = "❌ 指令參數不足！\n格式：/capacity MM/DD Court X\n範例：/capacity 10/31 PM 24"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                log_service.warning(
                    "/capacity 指令參數不足",
                    source_id=source_id,
                    user_id=user_id,
                    command=message_text.strip()
                )
                return
            
            # 參數完整，繼續處理
            from datetime import datetime
            today = datetime.now()
            
            # 解析日期
            month = int(capacity_data['date_str'].split('/')[0])
            day = int(capacity_data['date_str'].split('/')[1])
            
            # 判斷年份（如果月份/日期已過，用明年）
            year = today.year
            try:
                target_date = datetime(year, month, day)
            except ValueError:
                reply_text = "❌ 日期格式錯誤！"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                return
            
            # 檢查是否過期
            if target_date < today:
                reply_text = "❌ 場次已過期！"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                return
            
            # 檢查 Excel 檔案是否存在
            from app.engines.filename_engine import FilenameEngine
            filename_engine = FilenameEngine(EXCEL_BASE_PATH)
            filepath = filename_engine.get_filepath(capacity_data['date_str'], capacity_data['court'])
            
            if not filepath.exists():
                reply_text = f"❌ 場次不存在！\n日期：{capacity_data['date_str']}\n場次：{capacity_data['court']}\n請先建立公告。"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                return
            
            # TODO: 實作 capacity 調整邏輯
            try:
                # 讀取現有資料
                excel_data = excel_service.read_excel(capacity_data['date_str'], capacity_data['court'])
                
                if not excel_data:
                    reply_text = "❌ 無法讀取 Excel 檔案！"
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
                    return
                
                current_capacity = excel_data['capacity']
                name_list = excel_data['name_list']
                
                # 計算已報名人數（非空白）
                registered_count = sum(1 for name in name_list[:current_capacity] if name and name.strip())
                
                new_capacity = capacity_data['new_capacity']
                
                # 檢查是否減少名額且已報名人數超過新名額
                if new_capacity < current_capacity and new_capacity < registered_count:
                    reply_text = f"❌ 已報名人數={registered_count}，新名額數={new_capacity}，無法執行！"
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
                    log_service.warning(
                        "/capacity 失敗：已報名人數超過新名額",
                        source_id=source_id,
                        user_id=user_id,
                        data={'registered': registered_count, 'new_capacity': new_capacity}
                    )
                    return
                
                # 調整名額
                if new_capacity > current_capacity:
                    # 增加名額：擴充空位
                    while len(name_list) < new_capacity:
                        name_list.append('')
                elif new_capacity < current_capacity:
                    # 減少名額：截斷至新容量
                    name_list = name_list[:new_capacity]
                
                # 更新 capacity（保持候補名單不變）
                old_capacity = current_capacity
                current_capacity = new_capacity
                
                # 寫回 Excel
                excel_service.update_excel(
                    date_str=capacity_data['date_str'],
                    court=capacity_data['court'],
                    name_list=name_list,
                    capacity=current_capacity
                )
                
                # 回覆成功訊息
                reply_text = f"✅ 名額調整成功！\n日期：{capacity_data['date_str']}\n場次：{capacity_data['court']}\n\n名額：{old_capacity}人 → {current_capacity}人\n已報名：{registered_count}人"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                log_service.info(
                    "收到 /capacity 指令",
                    source_id=source_id,
                    user_id=user_id,
                    data={'old_capacity': old_capacity, 'new_capacity': current_capacity, 'registered': registered_count}
                )
            except Exception as e:
                error_msg = f"❌ 調整失敗：{str(e)}"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=error_msg)
                )
                log_service.error(
                    "/capacity 執行錯誤",
                    source_id=source_id,
                    user_id=user_id,
                    error=str(e)
                )
            return
        # /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

        
        if not all([log_service, parser, registration_engine, line_bot_api]):
            logger.error("服務未初始化")
            return

        log_service.info(
            "收到訊息",
            source_id=source_id,
            preview=message_text[:50]
        )

        try:
            # 先嘗試解析為批量操作
            batch_data = parser.parse_batch_operation(message_text)

            if batch_data:
                # 處理批量操作
                result = registration_engine.handle_batch_operation(batch_data)
            else:
                # 嘗試解析為批次報名
                batch_registrations = parser.parse_registration_batch(message_text)

                if batch_registrations:
                    # 處理批次報名
                    results = []
                    for reg in batch_registrations:
                        result = registration_engine.handle_registration(reg)
                        results.append(result)

                    # 組合成回覆訊息
                    if all(r.get('success') for r in results):
                        # 所有都成功，合併顯示
                        reply_message = "【批次報名結果】\n\n"
                        for i, (reg, result) in enumerate(zip(batch_registrations, results)):
                            sign = '+' if reg.num > 0 else ''
                            reply_message += f"{i+1}. {reg.name} {sign}{reg.num}: ✓\n"
                        reply_message += "\n" + results[0]['message']
                        result = {'success': True, 'message': reply_message}
                    else:
                        # 部分失敗
                        reply_message = "【批次報名結果】\n\n"
                        for i, (reg, result) in enumerate(zip(batch_registrations, results)):
                            sign = '+' if reg.num > 0 else ''
                            status = "成功" if result.get('success') else "失敗"
                            reply_message += f"{i+1}. {reg.name} {sign}{reg.num}: {status}\n"
                            if not result.get('success'):
                                reply_message += f"   → {result.get('message', '')}\n"
                        result = {'success': False, 'message': reply_message}
                else:
                    # 嘗試解析為單筆報名
                    registration = parser.parse_registration(message_text)

                    if registration:
                        result = registration_engine.handle_registration(registration)
                    else:
                        # 跳過複製 Bot 回覆的訊息（避免被誤判為公告）
                        if '【批次報名結果】' in message_text:
                            reply_text = "⚠️ 此為報名結果訊息，無法作為新場次公告使用。\n請按照格式發布完整公告訊息："
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=reply_text)
                            )
                            log_service.info(
                                "收到複製的 Bot 回覆訊息，拒絕處理",
                                source_id=source_id,
                                preview=message_text[:50]
                            )
                            return

                        # 嘗試解析為公告
                        announcement = parser.parse_announcement(message_text)

                        if announcement:
                            result = registration_engine.handle_announcement(announcement)
                        else:
                            # 不是可識別的訊息格式
                            return

            # 回覆訊息
            if result.get('success'):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=result['message'])
                )

                log_service.info(
                    "處理成功",
                    source_id=source_id,
                    action=result.get('action')
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=result['message'])
                )

                log_service.warning(
                    "處理失敗",
                    source_id=source_id,
                    error=result.get('message')
                )

        except Exception as e:
            error_msg = f"❌ 處理錯誤：{str(e)}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_msg)
            )
            log_service.error(
                "系統錯誤",
                source_id=source_id,
                error=str(e)
            )

    return handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 初始化服務
    log_service = LogService(LOG_DIR)
    filename_engine = FilenameEngine(EXCEL_BASE_PATH)
    excel_service = ExcelService(filename_engine)
    registration_engine = RegistrationEngine(excel_service)
    parser = MessageParser()
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    permission_service = PermissionService()

    # 存入全域變量
    _services.update({
        'log_service': log_service,
        'registration_engine': registration_engine,
        'parser': parser,
        'line_bot_api': line_bot_api,
        'permission_service': permission_service,
        'excel_service': excel_service
    })
    
    # 存入 app state
    app.state.log_service = log_service
    app.state.registration_engine = registration_engine
    app.state.parser = parser
    app.state.line_bot_api = line_bot_api
    app.state.webhook_handler = webhook_handler
    
    # 在 lifespan 內註冊處理器（確保服務已初始化）
    # 注意：LINE SDK 的 add() 是装饰器，需要直接用 __add_handler
    webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
    
    log_service.info("LINE 羽球報名系統啟動")
    yield
    log_service.info("LINE 羽球報名系統關閉")


app = FastAPI(
    title="LINE 群組羽球報名系統",
    version="1.0.0",
    description="自動處理 LINE 群組羽球活動報名",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "badminton-registration-bot"
    }


@app.get("/webhook/line")
async def webhook_get():
    """LINE webhook 驗證端點（GET 請求）"""
    return {"status": "ok"}

@app.post("/webhook/line")
async def webhook(request: Request):
    """LINE Webhook 端點"""
    from app.config import LINE_CHANNEL_SECRET
    from linebot.exceptions import InvalidSignatureError
    from linebot.models import MessageEvent, TextMessage
    import hmac as hmac_module
    import hashlib
    import base64
    from hmac import compare_digest
    
    signature = request.headers.get('X-Line-Signature')
    
    # 檢查 signature 是否存在
    if not signature:
        logger.warning("收到無 signature 的請求 (可能是測試)")
        return {"status": "ok", "note": "no signature (test request)"}

    # 讀取原始 body（不使用 FastAPI 的自動解析）
    body = b''
    async for chunk in request.stream():
        body += chunk
    
    logger.info(f"收到請求: body長度={len(body)}, signature前20字元={signature[:20] if signature else 'None'}")
    logger.info(f"body完整內容: {body}")
    
    try:
        # 檢查簽名是否匹配（使用原始 body bytes）
        generated_sig = base64.b64encode(
            hmac_module.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
        ).decode()
        
        logger.info(f"期望簽名: {generated_sig[:20]}...")
        logger.info(f"收到簽名: {signature[:20]}...")
        logger.info(f"簽名匹配: {compare_digest(generated_sig.encode(), signature.encode())}")
        
        if not compare_digest(generated_sig.encode(), signature.encode()):
            logger.error(f"簽名不匹配！")
            raise InvalidSignatureError(f"Invalid signature. signature={signature}")
        
        # 簽名驗證通過，調用 webhook handler 處理事件
        body_str = body.decode('utf-8')
        # 確保 handler 已註冊（--reload 模式下 lifespan 可能未執行）
        if not hasattr(app.state, 'webhook_handler') or not app.state.webhook_handler._handlers:
            from linebot.models import MessageEvent
            if not hasattr(app.state, 'webhook_handler'):
                from linebot import WebhookHandler
                app.state.webhook_handler = WebhookHandler(LINE_CHANNEL_SECRET)
            app.state.webhook_handler._WebhookHandler__add_handler(create_handler(), MessageEvent)
        app.state.webhook_handler.handle(body_str, signature)
        
        return {"status": "ok"}
        
    except InvalidSignatureError:
        if app.state.log_service:
            app.state.log_service.error("無效的簽章")
        raise HTTPException(status_code=400)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
