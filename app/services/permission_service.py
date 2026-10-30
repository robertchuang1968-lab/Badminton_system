"""
LINE 群組羽球報名系統 - 權限檢查服務
"""
import json
from pathlib import Path
from typing import List


class PermissionService:
    def __init__(self, managers_file: str = "app/data/admin_list.json"):
        """
        初始化權限檢查服務
        
        Args:
            managers_file: 管理人名單 JSON 檔案路徑
        """
        self.managers_file = Path(managers_file)
    
    def is_manager(self, user_id: str) -> bool:
        """
        檢查 user_id 是否為管理人
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            bool: 是否為管理人
        """
        if not self.managers_file.exists():
            return False
        
        try:
            with open(self.managers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            managers = data.get('managers', [])
            return user_id in managers
        except (json.JSONDecodeError, IOError):
            return False
    
    def add_manager(self, user_id: str) -> bool:
        """
        新增管理人
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            bool: 是否成功
        """
        if not self.managers_file.exists():
            data = {"managers": [], "updated_at": ""}
        else:
            try:
                with open(self.managers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                data = {"managers": [], "updated_at": ""}
        
        managers = data.get('managers', [])
        if user_id not in managers:
            managers.append(user_id)
            data['managers'] = managers
            data['updated_at'] = self._get_current_date()
            
            try:
                with open(self.managers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
            except IOError:
                return False
        return True  # 已存在也視為成功
    
    def remove_manager(self, user_id: str) -> bool:
        """
        移除管理人
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            bool: 是否成功
        """
        if not self.managers_file.exists():
            return False
        
        try:
            with open(self.managers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            managers = data.get('managers', [])
            if user_id in managers:
                managers.remove(user_id)
                data['managers'] = managers
                data['updated_at'] = self._get_current_date()
                
                with open(self.managers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
            return False
        except (json.JSONDecodeError, IOError):
            return False
    
    def get_managers(self) -> List[str]:
        """
        取得所有管理人列表
        
        Returns:
            List[str]: 管理人 user_id 列表
        """
        if not self.managers_file.exists():
            return []
        
        try:
            with open(self.managers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('managers', [])
        except (json.JSONDecodeError, IOError):
            return []
    
    def _get_current_date(self) -> str:
        """取得目前日期 (YYYY-MM-DD)"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')
