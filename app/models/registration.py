"""
LINE 群組羽球報名系統 - 數據模型
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnnouncementData:
    """公告訊息解析結果"""
    date_str: str  # 例如: "10/24"
    court: str  # AM 或 PM
    site: str  # 場地名稱
    time: str  # 時間範圍
    name_list: list  # 名單列表
    tail: Optional[str] = None  # 備註尾碼
    capacity: int = 24  # 名額數（從 Tail 解析）
    is_valid: bool = True  # 日期是否合法（False = 如 11/32 等無效日期）


@dataclass
class RegistrationData:
    """報名/取消報名解析結果"""
    """
    這段程式碼定義了一個名為 RegistrationData 的 Python 類別（Class），其主要功用是作為「報名與取消報名訊息的資料結構（Data Model）」。
    當系統透過解析器（Parser）從 LINE 訊息中抓取到使用者的報名意圖時，會把這些零散的資訊打包並存入這個類別的實例中，方便後續的引擎（如 registration_engine.py）進行商業邏輯判斷與處理。
    """
    date_str: str  # 例如: "10/24"
    court: str  # AM 或 PM
    name: str  # 報名者名字
    num: int  # +N 或 -N

    #------------------------------------------------------------------------
    # 2026/10/27 新增內容
    full_date: Optional[str] = None  # 完整日期，例如: "2026/10/24"
    is_expired: bool = False         # 是否已過期
    is_valid: bool = True            # 日期是否合法（False = 如 11/31 等無效日期）
    #------------------------------------------------------------------------
