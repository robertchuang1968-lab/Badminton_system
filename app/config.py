"""
LINE 群組羽球報名系統 - 配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# LINE Bot 憑證
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')

# Excel 儲存路徑
EXCEL_BASE_PATH = Path('/home/robert/workspace/LINE群組羽球報名系統/Data')

EXCEL_BACKUP_PATH = EXCEL_BASE_PATH / 'backup'

# 預設容量上限
MAX_CAPACITY = int(os.getenv('MAX_CAPACITY', '24'))

# 日誌路徑
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 確保備份目錄存在
EXCEL_BASE_PATH.mkdir(parents=True, exist_ok=True)
EXCEL_BACKUP_PATH.mkdir(parents=True, exist_ok=True)
