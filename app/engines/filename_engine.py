"""
LINE 群組羽球報名系統 - 檔名計算引擎
根據日期和場次計算 Excel 檔案名稱
"""
from datetime import datetime
from pathlib import Path
from app.config import EXCEL_BASE_PATH


class FilenameEngine:
    """檔名計算引擎"""
    
    def __init__(self, base_path: Path = EXCEL_BASE_PATH):
        self.base_path = base_path
    
    def generate_filename(self, date_str: str, court: str) -> Path:
        """
        根據日期和場次生成 Excel 檔案路徑
        
        Args:
            date_str: 日期字串，格式為 "MM/DD"
            court: 場次，AM 或 PM
            
        Returns:
            Excel 檔案的完整路徑
        """
        # 解析日期
        month, day = date_str.split('/')
        month_int = int(month)
        day_int = int(day)
        
        # 取得當前年份
        today = datetime.now()
        year = today.year
        
        # 嘗試解析目標日期
        try:
            target_date = datetime(year, month_int, day_int)
        except ValueError:
            # 日期無效，使用今天
            target_date = today
        
        # 如果目標日期小於今天，使用下一年
        if target_date.date() < today.date():
            year += 1
        
        # 生成檔名
        filename = f"{year}_{month_int}_{day_int}-{court}.xlsx"
        
        return self.base_path / filename
    
    def filename_exists(self, date_str: str, court: str) -> bool:
        """檢查檔案是否已存在"""
        filepath = self.generate_filename(date_str, court)
        return filepath.exists()
    
    def get_filepath(self, date_str: str, court: str) -> Path:
        """獲取檔案完整路徑"""
        return self.generate_filename(date_str, court)
