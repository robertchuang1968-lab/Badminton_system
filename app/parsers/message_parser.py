"""
LINE 群組羽球報名系統 - 訊息剖析器
解析 LINE 訊息並提取報名相關資訊
"""
import re
from datetime  import datetime
from typing import Optional, Tuple
from app.models.registration import AnnouncementData, RegistrationData


class MessageParser:
    """訊息剖析器"""
    
    # 日期格式：MM/DD
    DATE_PATTERN = r'(\d{1,2})/(\d{1,2})'
    
    # 場次格式：上午場/下午場/AM/PM
    #COURT_PATTERN = r'(上午場|下午場|AM|PM)'
    COURT_PATTERN = r'(上午場|下午場|(?i:AM|PM))'
    
    # 地點格式：地點：XXX 或 ✨地點：XXX
    SITE_PATTERN = r'(?:✨)?地點[：:]\s*(.+?)(?:\n|$)'
    
    # 時間格式：時間：XX:00-XX:00 或 XX:00~XX:00
    TIME_PATTERN = r'時間[：:]\s*(\d{1,2}:\d{2}[\-~]\d{1,2}:\d{2})'
    
    # 報名格式：日期 Court 名字 +/-N (單筆)
    # 支援名字包含括號，如：保耀(FB)+1 或 保耀（FB）+1
    REGISTRATION_PATTERN_SINGLE = r'(\d{1,2})/(\d{1,2})\s+(上午場|下午場|(?i:AM|PM))\s+([^\s]+(?:\s*[（(][^）)]*[）)])?)\s*([+-]\d+)$'

    # 報名格式：日期 Court 名字 +/-N 或 名單1 +/-N1, 名單2 +/-N2
    #REGISTRATION_PATTERN = r'(\d{1,2})/(\d{1,2})\s+(上午場|下午場|AM|PM)\s+([^\s,]+\s+[+-]\d+(?:\s*,\s*[^\s,]+\s+[+-]\d+)*)'
    REGISTRATION_PATTERN = r'(\d{1,2})/(\d{1,2})\s+(上午場|下午場|(?i:AM|PM))\s+([^\s,]+\s+[+-]\d+(?:\s*,\s*[^\s,]+\s+[+-]\d+)*)'

    # 批量操作格式：本次操作報名：名字1 +/-N1, 名字2 +/-N2
    BATCH_OPERATION_PATTERN = r'本次操作報名[：:]\\s*(.+)'
    
    # 容量調整指令格式：/capacity MM/DD Court X
    # 支援大小寫 AM/PM（(?i:AM|PM) 為 case-insensitive）
    CAPACITY_PATTERN = r'^/capacity\s+(\d{1,2})/(\d{1,2})\s+(上午場|下午場|(?i:AM|PM))\s+(\d+)$'
    
    def parse_capacity_command(self, message: str) -> Optional[dict]:
        """
        解析 /capacity 指令
        
        Args:
            message: LINE 訊息文字
            
        Returns:
            dict 包含 date_str, court, new_capacity
            或 None（如果格式不符合）
        """
        match = re.match(self.CAPACITY_PATTERN, message.strip())
        if not match:
            return None
        
        month, day, court_raw, capacity = match.groups()
        
        # 轉換 court
        court_map = {
            '上午場': 'AM',
            '下午場': 'PM',
            'am': 'AM',
            'AM': 'AM',
            'pm': 'PM',
            'PM': 'PM'
        }
        court = court_map.get(court_raw, court_raw.upper())
        
        # 組建日期字串 MM/DD
        date_str = f"{month}/{day}"
        
        return {
            'date_str': date_str,
            'court': court,
            'new_capacity': int(capacity)
        }

    def parse_batch_operation(self, message: str) -> Optional[dict]:
        """
        解析批量操作訊息
        支援兩種格式：
        1. 簡化格式：日期 Court 本次操作報名：名字1 +/-N1, 名字2 +/-N2, ...
        2. 完整格式（包含 Head）：日期 Court 資訊...\n本次操作報名：名字1 +/-N1, 名字2 +/-N2, ...

        Args:
            message: LINE 訊息文字

        Returns:
            dict 包含 date_str, court, operations (list of RegistrationData)
            或 None（如果格式不符合）
        """
        lines = message.strip().split('\n')
        first_line = lines[0].strip() if lines else ''

        # 格式1：簡化格式（第一行包含日期和場次）
        #full_pattern = r'(\d{1,2})/(\d{1,2})\s+(上午場|下午場|AM|PM)\s+本次操作報名[：:]\s*(.+)'
        full_pattern = r'(\d{1,2})/(\d{1,2})\s+(上午場|下午場|(?i:AM|PM))\s+本次操作報名[：:]\s*(.+)'
        full_match = re.match(full_pattern, first_line)

        if full_match:
            month = full_match.group(1)
            day = full_match.group(2)
            date_str = f"{month}/{day}"

            court_raw = full_match.group(3)
            court = self._normalize_court(court_raw)

            operations_str = full_match.group(4).strip()
        else:
            # 格式2：完整格式（多行，包含 Head 資訊）
            # 嘗試從第一行提取日期和場次
            #date_court_match = re.match(r'(\d{1,2}/\d{1,2})\s*（.*）?\s*(上午場|下午場|AM|PM)', first_line)
            date_court_match = re.match(r'(\d{1,2}/\d{1,2})\s*（.*）?\s*(上午場|下午場|(?i:AM|PM))', first_line)
            if not date_court_match:
                return None

            date_str = date_court_match.group(1)
            court_raw = date_court_match.group(2)
            court = self._normalize_court(court_raw)

            # 在所有行中查找「本次操作報名」
            operations_str = None
            for line in lines:
                if '本次操作報名' in line or '本次操作：' in line:
                    # 提取冒號後面的內容
                    match = re.search(r'[：:]\s*(.+)', line)
                    if match:
                        operations_str = match.group(1).strip()
                        break

            if not operations_str:
                return None

        # 解析操作列表
        operations = []
        items = re.split(r',\s*', operations_str)

        for item in items:
            item = item.strip()
            # 解析單個操作：名字 +/-N
            item_match = re.match(r'(.+?)\s+([+-]\d+)', item)
            if item_match:
                name = item_match.group(1).strip()
                num = int(item_match.group(2))
                # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                # 2026/10/28 新增程式碼
                # 2026/11/05 新增 is_valid 驗證
                full_date, is_expired, is_valid = self._calculate_expiry(date_str)
                operations.append(RegistrationData(
                    date_str=date_str,
                    court=court,
                    name=name,
                    num=num,
                    full_date=full_date,
                    is_expired=is_expired,
                    is_valid=is_valid
                ))
                # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        if not operations:
            return None

        return {
            'date_str': date_str,
            'court': court,
            'operations': operations
        }

    def parse_registration_batch(self, message: str) -> list:
        

      
        match = re.match(self.REGISTRATION_PATTERN, message.strip())

        if not match:
            return []

        month = match.group(1)
        day = match.group(2)
        date_str = f"{month}/{day}"

        court_raw = match.group(3)
        court = self._normalize_court(court_raw)

        # 解析多個報名者
        name_num_pairs = match.group(4)
        registrations = []

        # 分割多個報名項目 (用逗號分隔)
        items = re.split(r',\s*', name_num_pairs)

        for item in items:
            item = item.strip()
            # 解析單個報名者：名字 +/-N
            item_match = re.match(r'(.+?)\s+([+-]\d+)', item)
            if item_match:
                name = item_match.group(1).strip()
                num = int(item_match.group(2))

                # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                # 2026/10/28 新增程式碼
                # 2026/11/05 新增 is_valid 驗證
                full_date, is_expired, is_valid = self._calculate_expiry(date_str)
                registrations.append(RegistrationData(
                    date_str=date_str,
                    court=court,
                    name=name,
                    num=num,
                    full_date=full_date,
                    is_expired=is_expired,
                    is_valid=is_valid
                ))
                # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        return registrations
    
    def parse_announcement(self, message: str) -> Optional[AnnouncementData]:
        """
        解析手動公告訊息
        
        Args:
            message: LINE 訊息文字
            
        Returns:
            AnnouncementData 或 None（如果格式不符合）
        """
        # 檢查是否包含必要元素
        date_match = re.search(self.DATE_PATTERN, message)
        court_match = re.search(self.COURT_PATTERN, message)
        
        if not date_match or not court_match:
            return None
        
        # 提取日期
        month = date_match.group(1)
        day = date_match.group(2)
        date_str = f"{month}/{day}"
        
        # 正規化場次
        court_raw = court_match.group(1)
        court = self._normalize_court(court_raw)
        
        # 提取場地
        site_match = re.search(self.SITE_PATTERN, message)
        site = site_match.group(1).strip() if site_match else "未知場地"
        
        # 提取時間
        time_match = re.search(self.TIME_PATTERN, message)
        time = time_match.group(1) if time_match else "時間未指定"
        
        # 提取名單（數字開頭的行）
        name_list = self._extract_name_list(message)
        
        # 提取備註尾碼
        tail = self._extract_tail(message)
        
        # 從 Tail 解析名額數
        capacity = self._parse_capacity_from_tail(tail)
        
        # 驗證日期有效性
        full_date, is_expired, is_valid = self._calculate_expiry(date_str)
        
        return AnnouncementData(
            date_str=date_str,
            court=court,
            site=site,
            time=time,
            name_list=name_list,
            tail=tail,
            capacity=capacity,
            is_valid=is_valid
        )
    
    def parse_registration(self, message: str) -> Optional[RegistrationData]:

        match = re.match(self.REGISTRATION_PATTERN_SINGLE, message.strip())
        
        if not match:
            return None
        
        month = match.group(1)
        day = match.group(2)
        date_str = f"{month}/{day}"
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # 2026/10/28 新增程式碼
        # 2026/11/05 新增 is_valid 驗證
        full_date, is_expired, is_valid = self._calculate_expiry(date_str)
        # 不直接回傳 None，改回傳 is_valid=False 的物件，讓 main.py 能回覆「無效日期！」
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        
        court_raw = match.group(3)
        court = self._normalize_court(court_raw)
        
        name = match.group(4)
        num = int(match.group(5))

        
        return RegistrationData(
            date_str=date_str,
            court=court,
            name=name,
            num=num,
            #---------------------------------------------------------------------------------------------
            # 2026/10/27 新增
            full_date=full_date,
            is_expired=is_expired,
            is_valid=is_valid
            # 修改終點
            #---------------------------------------------------------------------------------------------
        )
    
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 2026/10/28  新增程式碼
    # 2026/11/05  新增 is_valid 驗證（拒絕無效日期如 11/31）
    def _calculate_expiry(self, date_str: str) -> tuple:
        """計算 full_date、is_expired 與 is_valid

        Returns:
            (full_date, is_expired, is_valid)
            - is_valid=False 表示日期無效（如 11/31），應拒絕處理
        """
        today = datetime.now()
        month, day = date_str.split('/')

        year = today.year
        if int(month) < today.month:
            year += 1  # 跨年份邊界

        full_date = f"{year}/{month}/{day}"

        is_expired = False
        is_valid = True
        try:
            target_date = datetime(year, int(month), int(day))
            if target_date.date() < today.date():
                is_expired = True
        except ValueError:
            # 日期無效（如 11/31、13/45），標記為不合法
            is_valid = False

        return full_date, is_expired, is_valid
    # 修改終點
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _normalize_court(self, court_raw: str) -> str:
        """正規化場次為 AM 或 PM"""
        court_map = {
            '上午場': 'AM',
            '下午場': 'PM',
            'AM': 'AM',
            'PM': 'PM'
        }
        return court_map.get(court_raw, court_raw.upper())
    
    def _extract_name_list(self, message: str) -> list:
        """從訊息中提取名單"""
        names = []
        lines = message.split('\n')
        
        for line in lines:
            # 匹配數字開頭的行：1. 名字 或 1 名字
            match = re.match(r'^\d+\.\s*(.+)$', line.strip())
            if match:
                name = match.group(1).strip()
                # 過濾掉非人名（如「後補」等）
                if name and not name.startswith('後補') and '限制' not in name:
                    names.append(name)
        
        return names
    
    def _extract_tail(self, message: str) -> Optional[str]:
        """提取備註尾碼 - 以關鍵字驅動，忽略前綴符號"""
        lines = message.split('\n')
        tail_lines = []
        in_tail = False

        for line in lines:
            stripped = line.strip()
            # 檢測 Tail 起始行：包含「限制」和「人」關鍵詞
            if '限制' in stripped and '人' in stripped:
                in_tail = True
                tail_lines.append(stripped)
            elif in_tail:
                # 已在 Tail 區塊中，繼續收集後續行（直到遇到非 Tail 行）
                # 非 Tail 行的判斷：不包含特殊符號或關鍵詞的行可能是正文或其他內容
                # 這裡假設 Tail 區塊由連續的特殊符號開頭行組成
                if stripped.startswith(('🌟', '🚨', '⚠️', '※', '📌')):
                    tail_lines.append(stripped)
                else:
                    break  # Tail 區塊結束

        return '\n'.join(tail_lines) if tail_lines else None

    def _parse_capacity_from_tail(self, tail: Optional[str]) -> int:
        """從 Tail 文字中解析容量（格式：「🌟限制（XX人）」）

        Args:
            tail: Tail 文字（可能為 None）

        Returns:
            容量數值，若無法解析則返回預設值 24
        """
        import re
        if not tail:
            return 24
        for line in tail.split('\n'):
            if '限制' in line and '人' in line:
                match = re.search(r'限制[（(](\d+)[人)]', line)
                if match:
                    capacity = int(match.group(1))
                    if capacity > 0:
                        return capacity
        return 24
