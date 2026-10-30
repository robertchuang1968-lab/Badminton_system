"""
LINE 群組羽球報名系統 - 日誌服務
"""
import logging
import json
from pathlib import Path
from datetime import datetime


class LogService:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 設置日誌格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 應用日誌
        self.logger = logging.getLogger('app')
        self.logger.setLevel(logging.INFO)
        
        # 文件處理器
        file_handler = logging.FileHandler(self.log_dir / 'app.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 錯誤日誌
        error_handler = logging.FileHandler(self.log_dir / 'error.log')
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str, **kwargs):
        log_data = {'message': message, **kwargs}
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def error(self, message: str, **kwargs):
        log_data = {'message': message, **kwargs}
        self.logger.error(json.dumps(log_data, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs):
        log_data = {'message': message, **kwargs}
        self.logger.warning(json.dumps(log_data, ensure_ascii=False))
