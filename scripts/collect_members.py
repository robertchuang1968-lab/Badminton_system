#!/usr/bin/env python3
"""
LINE 群組成員收集工具
收集群組中所有成員的 user_id 和 user_name，並儲存為 Excel 檔案
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import MessageEvent, TextMessage, SourceGroup
from linebot.exceptions import LineBotApiError

# 載入環境變數
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')

def get_group_members(group_id: str) -> list:
    """取得群組所有成員"""
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    
    members = []
    member_ids = []
    
    try:
        # 分页獲取所有成員
        next_cursor = None
        while True:
            response = line_bot_api.get_group_member_ids(
                group_id=group_id,
                start=next_cursor if next_cursor else None
            )
            member_ids.extend(response.member_ids)
            
            if not response.next_cursor:
                break
            next_cursor = response.next_cursor
            
        print(f"✅ 取得 {len(member_ids)} 個成員 ID")
        
        # 批量獲取成員資訊 (每次最多 100 人)
        for i in range(0, len(member_ids), 100):
            batch_ids = member_ids[i:i+100]
            try:
                response = line_bot_api.get_group_members_batch_detail(
                    group_id=group_id,
                    member_ids=batch_ids
                )
                for member in response.members:
                    members.append({
                        'user_id': member.user_id,
                        'display_name': member.display_name if hasattr(member, 'display_name') and member.display_name else '',
                        'picture_url': member.picture_url if hasattr(member, 'picture_url') and member.picture_url else ''
                    })
            except LineBotApiError as e:
                print(f"⚠️ 獲取成員批次失敗 (i={i}): {e}")
                
    except LineBotApiError as e:
        print(f"❌ 取得群組成員失敗: {e}")
        sys.exit(1)
    
    return members

def save_to_excel(members: list, output_path: str):
    """儲存成員資料到 Excel"""
    import pandas as pd
    
    # 準備資料
    data = []
    for idx, member in enumerate(members, 1):
        data.append({
            '序號': idx,
            'LINE ID': member['user_id'],
            '暱稱': member['display_name'],
            '頭像 URL': member['picture_url']
        })
    
    df = pd.DataFrame(data)
    
    # 寫入 Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='成員名單')
        
        # 調整欄位寬度
        ws = writer.sheets['成員名單']
        ws.column_dimensions['A'].width = 6   # 序號
        ws.column_dimensions['B'].width = 35  # LINE ID
        ws.column_dimensions['C'].width = 20  # 暱稱
        ws.column_dimensions['D'].width = 50  # 頭像 URL
    
    print(f"✅ 已儲存至: {output_path}")
    return output_path

def main():
    """主函式"""
    # 解析命令列參數
    parser = argparse.ArgumentParser(description='LINE 群組成員收集工具')
    parser.add_argument('--group-id', '-g', required=True, help='LINE 群組 ID')
    args = parser.parse_args()
    
    group_id = args.group_id
    
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ 錯誤: LINE_CHANNEL_ACCESS_TOKEN 未設定")
        sys.exit(1)
    
    print("=" * 50)
    print("LINE 群組成員收集工具")
    print("=" * 50)
    print(f"群組 ID: {group_id}")
    print()
    
    # 取得成員
    print("📋 正在取得群組成員...")
    members = get_group_members(group_id)
    
    if not members:
        print("❌ 沒有取得到成員資料")
        sys.exit(1)
    
    # 產生輸出檔案
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent / 'Data'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'group_members_{timestamp}.xlsx'
    
    # 儲存
    save_to_excel(members, str(output_path))
    
    print()
    print("=" * 50)
    print(f"收集完成！共 {len(members)} 人")
    print("=" * 50)

if __name__ == '__main__':
    main()
