"""解析器測試"""
import pytest
from app.parsers.message_parser import MessageParser


@pytest.fixture
def parser():
    return MessageParser()


class TestMessageParser:
    """訊息剖析器測試"""
    
    def test_parse_announcement_basic(self, parser):
        """測試基本公告解析"""
        message = """10/24（星期六）歡樂羽球下午場🏸
✨地點：晴天羽球館
費用：270元/人
時間：14:00-17:00
1. 浩雅
2. 阿瑋
3. 黃保輝
後補：1."""
        
        result = parser.parse_announcement(message)
        
        assert result is not None
        assert result.date_str == "10/24"
        assert result.court == "PM"
        assert result.site == "晴天羽球館"
        assert result.time == "14:00-17:00"
        assert len(result.name_list) == 3
    
    def test_parse_announcement_missing_date(self, parser):
        """測試缺少日期的公告"""
        message = "這是普通的聊天訊息"
        result = parser.parse_announcement(message)
        assert result is None
    
    def test_parse_registration_signup(self, parser):
        """測試報名解析"""
        message = "10/24 PM Robert +1"
        result = parser.parse_registration(message)
        
        assert result is not None
        assert result.date_str == "10/24"
        assert result.court == "PM"
        assert result.name == "Robert"
        assert result.num == 1
    
    def test_parse_registration_unsignup(self, parser):
        """測試取消報名解析"""
        message = "10/24 PM Mike -1"
        result = parser.parse_registration(message)
        
        assert result is not None
        assert result.num == -1
    
    def test_parse_registration_invalid_format(self, parser):
        """測試無效格式的報名"""
        message = "隨便說點什麼"
        result = parser.parse_registration(message)
        assert result is None
    
    def test_normalize_court(self, parser):
        """測試場次正規化"""
        assert parser._normalize_court("上午場") == "AM"
        assert parser._normalize_court("下午場") == "PM"
        assert parser._normalize_court("AM") == "AM"
        assert parser._normalize_court("PM") == "PM"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
