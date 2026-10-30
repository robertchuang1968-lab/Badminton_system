"""
生成測試 Excel 檔案（模擬真實場景）
"""
from app.parsers.message_parser import MessageParser
from app.engines.filename_engine import FilenameEngine
from app.services.excel_service import ExcelService
from app.engines.registration_engine import RegistrationEngine
from app.models.registration import AnnouncementData, RegistrationData


def main():
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
後補：1.（空白）
🌟限制（24人），候補可報名，但要候補到才可來打喔！
🌟新人請看記事本
🌟到場繳費簽名時，請在簿子簽上您的號碼跟名字（務必跟群組報名一致，以利對帳）"""
    
    parser = MessageParser()
    announcement = parser.parse_announcement(message)
    
    print("📋 公告訊息解析結果：")
    print(f"   日期: {announcement.date_str}")
    print(f"   場次: {announcement.court}")
    print(f"   場地: {announcement.site}")
    print(f"   時間: {announcement.time}")
    print(f"   名單: {len(announcement.name_list)} 人")
    
    # 建立引擎
    filename_engine = FilenameEngine()
    excel_service = ExcelService(filename_engine)
    registration_engine = RegistrationEngine(excel_service)
    
    # 處理公告
    result = registration_engine.handle_announcement(announcement)
    
    if result['success']:
        print(f"\n✅ 公告處理成功")
        print(f"   檔案路徑: {result.get('filepath')}")
        print(f"   回覆訊息:\n{result['message']}")
    else:
        print(f"\n⚠️ 公告處理失敗: {result['message']}")
    
    # 測試報名
    print("\n📝 測試報名邏輯：")
    test_registrations = [
        ("10/24", "PM", "Alice", 1),
        ("10/24", "PM", "Bob", 1),
        ("10/24", "PM", "Alice", -1),
    ]
    
    for date_str, court, name, num in test_registrations:
        reg = RegistrationData(date_str=date_str, court=court, name=name, num=num)
        result = registration_engine.handle_registration(reg)
        print(f"   {name} {'+1' if num > 0 else '-1'}: {'✅' if result['success'] else '❌'} {result['message'][:50]}...")
    
    # 列出生成的檔案
    print("\n📁 生成的 Excel 檔案：")
    for f in sorted(filename_engine.base_path.glob("*.xlsx")):
        print(f"   {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
