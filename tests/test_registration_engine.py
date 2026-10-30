"""註冊引擎測試"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.engines.registration_engine import RegistrationEngine
from app.models.registration import RegistrationData, AnnouncementData
from app.parsers.message_parser import MessageParser


@pytest.fixture
def mock_excel_service():
    """模擬 Excel 服務"""
    service = Mock()
    service.read_excel.return_value = {
        'head': ['10/24 下午場', '地點：晴天羽球館'],
        'name_list': ['浩雅', '阿瑋'],
        'tail': ['備註']
    }
    return service


@pytest.fixture
def engine(mock_excel_service):
    return RegistrationEngine(mock_excel_service)


class TestRegistrationEngine:
    """報名引擎測試"""
    
    def test_handle_announcement_new(self, engine):
        """測試建立新公告"""
        announcement = AnnouncementData(
            date_str="10/25",
            court="PM",
            site="晴天羽球館",
            time="14:00-17:00",
            name_list=["浩雅", "阿瑋"]
        )
        
        with patch.object(engine.filename_engine, 'get_filepath') as mock_path:
            mock_path.return_value.exists.return_value = False
            with patch.object(engine.excel_service, 'create_new_excel') as mock_create:
                mock_create.return_value = "/test/path.xlsx"
                
                result = engine.handle_announcement(announcement)
                
                assert result['success'] is True
                assert result['action'] == 'created'
    
    def test_handle_announcement_existing(self, engine):
        """測試公告已存在的情況"""
        announcement = AnnouncementData(
            date_str="10/24",
            court="PM",
            site="晴天羽球館",
            time="14:00-17:00",
            name_list=["浩雅"]
        )
        
        with patch.object(engine.filename_engine, 'get_filepath') as mock_path:
            mock_path.return_value.exists.return_value = True
            
            result = engine.handle_announcement(announcement)
            
            assert result['success'] is False
            assert "已存在" in result['message']
    
    def test_handle_registration_not_found(self, engine):
        """測試報名時檔案不存在"""
        registration = RegistrationData(
            date_str="99/99",
            court="PM",
            name="Robert",
            num=1
        )
        
        with patch.object(engine.filename_engine, 'get_filepath') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            result = engine.handle_registration(registration)
            
            assert result['success'] is False
            assert "未開場" in result['message']
            assert "請洽團主" in result['message']
    
    def test_handle_signup_duplicate(self, engine):
        """測試重複報名"""
        registration = RegistrationData(
            date_str="10/24",
            court="PM",
            name="浩雅",
            num=1
        )
        
        result = engine._handle_signup(registration, engine.excel_service.read_excel("10/24", "PM"))
        
        assert result['success'] is False
        assert "名額已滿" in result['message']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
