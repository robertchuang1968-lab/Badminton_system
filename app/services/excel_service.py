"""
LINE 群組羽球報名系統 - Excel 服務
處理 Excel 檔案的讀寫操作
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from app.config import EXCEL_BASE_PATH, MAX_CAPACITY
from app.engines.filename_engine import FilenameEngine


class ExcelService:
    """Excel 檔案服務"""
    
    def __init__(self, filename_engine: FilenameEngine):
        self.filename_engine = filename_engine
    
    def create_new_excel(self, date_str: str, court: str, announcement: dict, capacity: int = 24) -> Path:
        """
        建立新的 Excel 檔案

        Args:
            date_str: 日期字串 (MM/DD)
            court: 場次 (AM/PM)
            announcement: 公告資料字典，包含 site, time, name_list, tail

        Returns:
            建立的 Excel 檔案路徑
        """
        filepath = self.filename_engine.get_filepath(date_str, court)

        # 準備資料
        head_lines = [
            f"{date_str}（{self._get_weekday(date_str)}）歡樂羽球{self._get_court_name(court)}",
            f"✨地點：{announcement['site']}",
            f"費用：270元/人",
            f"時間：{announcement['time']}"
        ]

        # 分離正取與候補名單
        regular_names = [n for n in announcement['name_list'] if n and not str(n).startswith('候')]
        substitute_names = [n for n in announcement['name_list'] if n and str(n).startswith('候')]

        # 從 announcement 中獲取容量，若無則使用傳入的 capacity
        tail_text = announcement.get('tail', '')
        parsed_capacity = self._parse_capacity_from_tail([tail_text] if tail_text else [])
        capacity = parsed_capacity if parsed_capacity != 24 else capacity

        # 建立 DataFrame
        data = {
            'No': [],
            'Name': []
        }

        # 填入正取名單 (編號 1 ~ capacity)
        for i, name in enumerate(regular_names, 1):
            data['No'].append(i)
            data['Name'].append(name)

        # 補滿正取空位至 capacity
        for i in range(len(regular_names) + 1, capacity + 1):
            data['No'].append(i)
            data['Name'].append('')

        # 填入候補名單 (編號從 capacity + 1 開始)
        for i, name in enumerate(substitute_names, capacity + 1):
            data['No'].append(i)
            data['Name'].append(name)

        df = pd.DataFrame(data)

        # 寫入 Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Head 部分
            pd.DataFrame({'Info': head_lines}).to_excel(
                writer, index=False, header=False, startrow=0
            )

            # 名單部分
            df.to_excel(writer, index=False, header=False, startrow=5)

            # Tail 部分（若未提供則使用預設值）
            tail_text = announcement.get('tail')
            if not tail_text:
                # 使用規格書預設 Tail
                tail_text = f'''🌟限制（{capacity}人），候補可報名，但要候補到才可來打喔！
🌟新人請看記事本
🌟到場繳費簽名時，請在簿子簽上您的號碼跟名字（務必跟群组報名一致，以利對帳）'''
            if tail_text:
                tail_lines = tail_text.split('\n')
                pd.DataFrame({'Info': tail_lines}).to_excel(
                    writer, index=False, header=False, startrow=len(df) + 6
                )

        return filepath
    
    def update_excel(self, date_str: str, court: str, name_list: list, capacity: int = 24) -> Path:
        """
        更新現有 Excel 檔案

        Args:
            date_str: 日期字串 (MM/DD)
            court: 場次 (AM/PM)
            name_list: 新的名單列表 (正取在前，候補在後)

        Returns:
            更新的 Excel 檔案路徑
        """
        filepath = self.filename_engine.get_filepath(date_str, court)

        #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        #  2026/10/28 新增程式碼：檢查 Excel 是否被鎖定
        lock_file = filepath.parent / f"~${filepath.name}"
        if lock_file.exists():
            raise Exception("⚠️ Excel 檔案正在使用，請關閉 Excel 後再報名")

        try:
            df_existing = pd.read_excel(filepath, sheet_name=0, header=None)
        except ValueError as e:
            raise Exception(f"⚠️ Excel 檔案格式錯誤，請連絡管理人員")
        #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        # 保留 Head（前 4 行）
        head_data = df_existing.iloc[:4].values.tolist()

        # 從現有 Tail 解析容量
        tail_lines = []
        for idx in range(len(df_existing) - 1, max(4, len(df_existing) - 5), -1):
            cell_value = df_existing.iloc[idx, 0]
            if isinstance(cell_value, str) and cell_value.startswith('🌟'):
                tail_lines.insert(0, cell_value)
            else:
                break
        capacity = self._parse_capacity_from_tail(tail_lines)

        """# 分離正取與候補名單
        regular_names = [n for n in name_list if n and not str(n).startswith('候')]
        substitute_names = [n for n in name_list if n and str(n).startswith('候')]"""
        # 新代碼：按 capacity 分隔正取與候補
        regular_names = name_list[:capacity]
        substitute_names = name_list[capacity:]

        # 準備新的名單 (正取編號 1~capacity，候補編號從 capacity+1 開始)
        new_data = []

        # 正取部分
        for i, name in enumerate(regular_names, 1):
            new_data.append([i, name])

        # 補滿正取空位
        for i in range(len(regular_names) + 1, capacity + 1):
            new_data.append([i, ''])

        # 候補部分 (從 capacity + 1 開始編號)
        for i, name in enumerate(substitute_names, capacity + 1):
            new_data.append([i, name])

        # 寫入 Excel（使用 openpyxl 直接操作，確保清除舊資料）
        from openpyxl import load_workbook
        try:
            wb = load_workbook(filepath)
            ws = wb.active

            # 清除舊的名單和 Tail（保留 Head）
            for row in range(6, ws.max_row + 1):
                for col in range(1, 3):
                    ws.cell(row=row, column=col).value = None

            # 寫入 Head（確保正確）
            for i, line in enumerate(head_data, 1):
                ws.cell(row=i, column=1).value = line[0] if line else None

            # 寫入新名單
            for i, row_data in enumerate(new_data, 6):
                ws.cell(row=i, column=1).value = row_data[0]
                ws.cell(row=i, column=2).value = row_data[1]

            # 寫入 Tail
            if tail_lines:
                tail_start_row = len(new_data) + 6
                for i, tail_line in enumerate(tail_lines):
                    ws.cell(row=tail_start_row + i, column=1).value = tail_line

            wb.save(filepath)
            wb.close()
        except PermissionError:
            raise Exception("後台Excel被鎖定")

        return filepath
    
    def read_excel(self, date_str: str, court: str) -> dict:
        """
        讀取 Excel 檔案

        Args:
            date_str: 日期字串 (MM/DD)
            court: 場次 (AM/PM)

        Returns:
            包含 head, name_list, tail, capacity, regular_empty_count 的字典
        """
        filepath = self.filename_engine.get_filepath(date_str, court)

        if not filepath.exists():
            return None

        # 檢查 Windows Excel 鎖定檔 (~$ 開頭的暫存檔)
        lock_file = filepath.parent / f"~${filepath.name}"
        if lock_file.exists():
            raise Exception("⚠️ Excel 檔案正在使用，請關閉 Excel 後再報名")
        
        
        
        # 檢查是否為空檔案
        if filepath.stat().st_size == 0:
            raise Exception("⚠️ Excel 檔案為空，請重新建立場次")

        try:
            # 讀取所有 sheet
            excel_file = pd.ExcelFile(filepath)
        except ValueError as e:
            if "engine" in str(e).lower():
                raise Exception("⚠️ Excel 檔案格式錯誤，請連絡管理人員")
            raise

        # 讀取第一個 sheet
        df = pd.read_excel(excel_file, sheet_name=0, header=None)

        # 提取 Head（前 4 行）
        head = df.iloc[:4, 0].dropna().tolist()

        # 提取 Name_List（第 5 行開始，Row index 5+）
        # 正取範圍：Row 6-29 (index 5-28)，對應 No.1-24
        # 候補範圍：Row 30+ (index 29+)
        all_values = df.iloc[5:, 1].tolist()

        # 分離正取與候補
        # 假設 capacity 為 24，則前 24 個是正取，之後是候補
        # 但我們需要先知道 capacity，所以先讀 Tail
        tail = []
        for idx in range(len(df) - 1, max(4, len(df) - 5), -1):
            cell_value = df.iloc[idx, 0]
            if isinstance(cell_value, str) and cell_value.startswith('🌟'):
                tail.insert(0, cell_value)
            else:
                break

        capacity = self._parse_capacity_from_tail(tail)

        # 分離正取與候補
        # 正取範圍：index 0 ~ capacity-1
        # 候補範圍：index capacity 開始，直到遇到 Tail（🌟開頭）
        regular_values = all_values[:capacity]
        remaining_values = all_values[capacity:]

        # 處理正取名單（保留空位）
        regular_names = []
        empty_positions = []
        for i, val in enumerate(regular_values):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                empty_positions.append(i)
                regular_names.append('')
            else:
                regular_names.append(str(val) if val else '')

        # 處理候補名單（跳過 Tail）
        substitute_names = []
        for val in remaining_values:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                break  # 遇到空白就停止（沒有候補）
            if isinstance(val, str) and val.startswith('🌟'):
                break  # 遇到 Tail 就停止
            substitute_names.append(str(val))

        # 合併：正取在前，候補在後
        name_list = regular_names + substitute_names

        return {
            'head': head,
            'name_list': name_list,
            'regular_empty_positions': empty_positions,
            'capacity': capacity,
            'tail': tail
        }
    
    def _get_weekday(self, date_str: str) -> str:
        """取得星期幾"""
        month, day = date_str.split('/')
        today = datetime.now()
        year = today.year
        
        try:
            date_obj = datetime(year, int(month), int(day))
        except ValueError:
            return "未知"
        
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[date_obj.weekday()]
    
    def _parse_capacity_from_tail(self, tail: list) -> int:
        """從 Tail 文字中解析容量（格式：「🌟限制（XX人）」）

        Args:
            tail: Tail 文字列表

        Returns:
            容量數值，若無法解析則返回預設值 MAX_CAPACITY
        """
        import re
        for line in tail:
            if isinstance(line, str) and '限制' in line and '人' in line:
                match = re.search(r'限制[（(](\d+)[人）)]', line)
                if match:
                    capacity = int(match.group(1))
                    # 驗證是否為 8 的倍數
                    if capacity > 0 and capacity % 8 == 0:
                        return capacity
        return MAX_CAPACITY

    def _get_court_name(self, court: str) -> str:
        """將 AM/PM 轉換為中文場次名稱"""
        return '上午場' if court == 'AM' else '下午場'
