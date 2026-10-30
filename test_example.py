"""
測試 Excel 檔案生成（模擬 LINE 訊息處理）
"""
from pathlib import Path
from app.parsers.message_parser import MessageParser
from app.engines.filename_engine import FilenameEngine
from app.services.excel_service import ExcelService
from app.engines.registration_engine import RegistrationEngine


def test_announcement_to_excel():
    """測試公告訊息轉 Excel"""
    # 模擬截圖中的LINE訊息
    message = """10/24（星期六）歡樂羽球下午場🏸
✨地點：晴天羽球館
費用：270元/人
時間：14:00-17:00
1. 浩雅
2. 阿瑋
3. 黃保輝
4. TSAI
5. Robert
6. hank
7. 芸熙
8. 子銓
9. 陳
10. 陳
11. Tom
12. 嬅
13–24：空白（尚未報名）
後補：1.（空白）
🌟限制（24人），候補可報名，但要候補到才可來打喔！
🌟新人請看記事本
🌟到場繳費簽名時，請在簿子簽上您的號碼跟名字（務必跟群組報名一致，以利對帳）"""
    
    parser = MessageParser()
    announcement = parser.parse_announcement(message)
    
    print(f"✅ 解析成功")
    print(f"   日期: {announcement.date_str}")
    print(f"   場次: {announcement.court}")
    print(f"   場地: {announcement.site}")
    print(f"   時間: {announcement.time}")
    print(f"   名單: {len(announcement.name_list)} 人")
    print(f"   名單內容: {announcement.name_list}")
    
    # 計算檔案路徑
    engine = FilenameEngine()
    filepath = engine.get_filepath(announcement.date_str, announcement.court)
    print(f"\n📁 預期檔案路徑: {filepath}")
    
    # 檢查檔案是否存在
    exists = filepath.exists()
    print(f"   檔案已存在: {exists}")
    
    return announcement


def test_registration():
    """測試報名邏輯"""
    parser = MessageParser()
    
    # 模擬報名訊息
    messages = [
        "10/24 PM Robert +1",
        "10/24 PM Mike -1",
        "10/25 AM Alice +1"
    ]
    
    for msg in messages:
        result = parser.parse_registration(msg)
        if result:
            print(f"✅ 解析: {msg}")
            print(f"   → {result}")
        else:
            print(f"⚠️ 無法解析: {msg}")


if __name__ == "__main__":
    print("=" * 50)
    print("測試 1: 公告訊息解析")
    print("=" * 50)
    announcement = test_announcement_to_excel()
    
    print("\n" + "=" * 50)
    print("測試 2: 報名訊息解析")
    print("=" * 50)
    test_registration()
    
    print("\n" + "=" * 50)
    print("🎉 所有測試完成！")
    print("=" * 50)
