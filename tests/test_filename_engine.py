"""檔名引擎測試"""
import pytest
from pathlib import Path
from app.engines.filename_engine import FilenameEngine
from datetime import datetime


@pytest.fixture
def engine():
    return FilenameEngine()


class TestFilenameEngine:
    """檔名引擎測試"""
    
    def test_generate_filename_future(self, engine):
        """測試生成未來日期的檔名"""
        filepath = engine.generate_filename("12/25", "PM")
        filename = filepath.name
        
        # 應該是今年的年份（如果 12/25 還沒到）
        current_year = datetime.now().year
        assert f"{current_year}_12_25-PM.xlsx" in str(filepath) or \
               f"{current_year+1}_12_25-PM.xlsx" in str(filepath)
    
    def test_generate_filename_past(self, engine):
        """測試生成過去日期的檔名"""
        # 使用一個已經過去的日期（例如今年的 1/1）
        filepath = engine.generate_filename("1/1", "AM")
        filename = filepath.name
        
        # 應該是明年的年份
        current_year = datetime.now().year
        assert f"{current_year+1}_1_1-AM.xlsx" in str(filepath)
    
    def test_filename_exists_not_found(self, engine):
        """測試檢查不存在的檔案"""
        exists = engine.filename_exists("1/1", "AM")
        assert exists is False
    
    def test_get_filepath(self, engine):
        """測試獲取檔案路徑"""
        filepath = engine.get_filepath("10/24", "PM")
        
        assert isinstance(filepath, Path)
        assert filepath.suffix == ".xlsx"
        assert "10_24-PM.xlsx" in str(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
