"""
LINE 群組羽球報名系統 - 報名引擎
處理報名和取消報名的核心邏輯
"""
import threading
from typing import Optional
from app.models.registration import RegistrationData, AnnouncementData
from app.services.excel_service import ExcelService
from app.config import MAX_CAPACITY
from app.engines.filename_engine import FilenameEngine


class RegistrationEngine:
    """報名引擎"""
    
    def __init__(self, excel_service: ExcelService):
        self.excel_service = excel_service
        self.filename_engine = FilenameEngine()
        self._lock = threading.Lock()
    
    def handle_announcement(self, announcement: AnnouncementData) -> dict:
        """
        處理手動公告
        
        Args:
            announcement: 公告資料
            
        Returns:
            處理結果字典
        """
        with self._lock:
            # 檢查日期是否有效
            if not announcement.is_valid:
                return {
                    'success': False,
                    'message': "⚠️ 無效日期！月份或日期超出範圍（如 11/32）。\n請使用有效日期重新發布公告。"
                }
            
            filepath = self.filename_engine.get_filepath(announcement.date_str, announcement.court)
            
            if filepath.exists():
                # 檔案已存在，返回錯誤
                return {
                    'success': False,
                    'message': f"⚠️ {announcement.date_str} {self._get_court_name(announcement.court)} 的報名表已存在，請使用報名/取消報名功能"
                }
            
            # 建立新 Excel
            announcement_dict = {
                'site': announcement.site,
                'time': announcement.time,
                'name_list': announcement.name_list,
                'tail': announcement.tail
            }
            
            try:
                filepath = self.excel_service.create_new_excel(
                    announcement.date_str,
                    announcement.court,
                    announcement_dict,
                    capacity=announcement.capacity
                )
                
                # 準備回覆訊息
                reply_message = self._format_reply(
                    announcement.date_str,
                    announcement.court,
                    announcement.name_list,
                    capacity=announcement.capacity
                )
                
                return {
                    'success': True,
                    'message': reply_message,
                    'filepath': str(filepath),
                    'action': 'created'
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'message': f"❌ 建立檔案失敗：{str(e)}"
                }
    
    def handle_registration(self, registration: RegistrationData) -> dict:
        """
        處理報名或取消報名

        Args:
            registration: 報名資料

        Returns:
            處理結果字典
        """
        with self._lock:
            
            # -------------------------------------------------------------------------------------------------------------------------------
            # 2026/10/27 新增程式碼
            """ 檢查報名日期是否已過期 （例如：10/25 PM Vic +1）  """
            if registration.is_expired:
                return {
                    'success': False,
                    'message': f"⚠️ {registration.date_str} {self._get_court_name(registration.court)} 已過期，請報名其它場次"
                }
            # -------------------------------------------------------------------------------------------------------------------------------
            
            
            filepath = self.filename_engine.get_filepath(registration.date_str, registration.court)

            if not filepath.exists():
                return {\
                    'success': False,
                    'message': f"⚠️ 目前 {registration.date_str} {self._get_court_name(registration.court)} 未開場，請洽團主或報名其它場次"
                }

            # 檢查 Excel 檔案是否可寫入（避免鎖定狀態下繼續執行）
            """try:
                with open(filepath, 'r+b') as f:
                    pass
            except PermissionError:
                return {
                    'success': False,
                    'message': "報名失敗，後台Excel被鎖定，請關閉Excel後再試"
                }
            except Exception:
                pass  # 其他錯誤（如唯讀檔案）不阻擋 """

            # 讀取現有資料
            excel_data = self.excel_service.read_excel(registration.date_str, registration.court)

            # 使用動態容量（優先用 Excel 中的容量，fallback 到環境變數）
            capacity = excel_data.get('capacity', MAX_CAPACITY)

            if registration.num > 0:
                # 報名邏輯
                return self._handle_signup(registration, excel_data)
            else:
                # 取消報名邏輯
                return self._handle_unsignup(registration, excel_data)

    def handle_batch_operation(self, batch_data: dict) -> dict:
        """
        處理批量操作

        Args:
            batch_data: dict 包含 date_str, court, operations (list of RegistrationData)

        Returns:
            處理結果字典
        """
        with self._lock:
            date_str = batch_data['date_str']
            court = batch_data['court']
            operations = batch_data['operations']

            filepath = self.filename_engine.get_filepath(date_str, court)

            # 檢查 Excel 檔案是否可寫入
            """try:
                with open(filepath, 'r+b') as f:
                    pass
            except PermissionError:
                return {
                    'success': False,
                    'message': "報名失敗，後台Excel被鎖定，請關閉Excel後再試"
                }
            except Exception:
                pass                      """

            # -----------------------------------------------------------------------------------------------------------
            # 2026/10/27 新增程式碼
            """ 檢查批次操作中的每個報名者日期是否過期 """
            for reg in operations:
                if reg.is_expired:
                    return {
                        'success': False,
                        'message': f"⚠️ {reg.date_str} {self._get_court_name(reg.court)} 已過期，請報名其它場次"
                    }
                if not reg.is_valid:
                    return {
                        'success': False,
                        'message': "⚠️ 無效日期！月份或日期超出範圍（如 11/31）。\n請使用有效日期重新輸入。"
                    }
            # 修改終點
            # -----------------------------------------------------------------------------------------------------------

            if not filepath.exists():
                return {
                    'success': False,
                    'message': f"⚠️ 目前 {date_str} {self._get_court_name(court)} 未開場，請洽團主或報名其它場次"
                }

            # 讀取現有資料
            excel_data = self.excel_service.read_excel(date_str, court)
            capacity = excel_data.get('capacity', MAX_CAPACITY)

            # 執行所有操作
            results = []
            for reg in operations:
                if reg.num > 0:
                    result = self._handle_signup(reg, excel_data)
                else:
                    result = self._handle_unsignup(reg, excel_data)
                results.append(result)

                # 更新 excel_data（因為名單已改變）
                if result.get('success'):
                    excel_data = self.excel_service.read_excel(date_str, court)

            # 組合成回覆訊息
            success_count = sum(1 for r in results if r.get('success'))
            fail_count = len(results) - success_count

            reply_message = f"【批量操作結果】\n\n"

            for i, (reg, result) in enumerate(zip(operations, results)):
                sign = '+' if reg.num > 0 else ''
                status = "✓" if result.get('success') else "✗"
                reply_message += f"{i+1}. {reg.name} {sign}{reg.num}: {status}\n"

                if not result.get('success'):
                    reply_message += f"   → {result.get('message', '')}\n"

            # 取得最終名單
            final_data = self.excel_service.read_excel(date_str, court)
            capacity = final_data.get('capacity', MAX_CAPACITY)
            reply_message += "\n" + self._format_reply(date_str, court, final_data['name_list'], capacity=capacity)

            return {
                'success': success_count == len(operations),
                'message': reply_message,
                'success_count': success_count,
                'fail_count': fail_count,
                'action': 'batch_operation'
            }
    
    def _handle_signup(self, registration: RegistrationData, excel_data: dict) -> dict:
        """處理報名 - 方案B：直接索引賦值重建名單（允許重複報名）"""
        current_list = excel_data['name_list']
        capacity = excel_data.get('capacity', MAX_CAPACITY)
        empty_positions = excel_data.get('regular_empty_positions', [])

        # 計算可用空位數量
        available_spots = len(empty_positions)
        """ mark line 209~213, 目的，當名額已滿時，可以啟用 line 226~232 候補邏輯"""
        #if available_spots <= 0:
        #    return {
        #        'success': False,
        #        'message': f"⚠️ {registration.date_str} {self._get_court_name(registration.court)} 名額已滿！"
        #    }

        # 重建名單：直接賦值到空位（不檢查重複）
        new_list = current_list.copy()
        filled = 0

        for pos in empty_positions:
            if filled >= registration.num:
                break
            # 直接賦值，不 insert
            new_list[pos] = registration.name
            filled += 1

        # 如果還有剩餘，添加到候補（保留原始名字）
        remaining = registration.num - filled
        if remaining > 0:
            #hou_count = len([n for n in new_list if n and n.startswith('候')]) + 1
            for _ in range(remaining):
                #new_list.append(f"候{hou_count}")
                #hou_count += 1
                new_list.append(registration.name)

        # 更新 Excel
        self.excel_service.update_excel(registration.date_str, registration.court, new_list, capacity=capacity)

        # 準備回覆（包含 Head 和 Tail）
        reply_message = self._format_reply(
            registration.date_str,
            registration.court,
            new_list,
            head=excel_data.get('head'),
            tail=excel_data.get('tail'),
            capacity=capacity
        )

        return {
            'success': True,
            'message': reply_message,
            'action': 'signup'
        }
    
    def _handle_unsignup(self, registration: RegistrationData, excel_data: dict) -> dict:
        """處理取消報名 - 優先刪除候補，再刪除正取"""
        current_list = excel_data['name_list']
        capacity = excel_data.get('capacity', MAX_CAPACITY)

        # 計算符合的名字數量（使用精確匹配，避免 "Jo" 匹配 "Joshua"）
        match_count = sum(1 for n in current_list if n and n.strip() == registration.name.strip())

        if match_count < abs(registration.num):
            return {
                'success': False,
                'message': f"{registration.date_str} {self._get_court_name(registration.court)} 場中，{registration.name} 報名數={match_count}，< 你要取消的筆數{abs(registration.num)}，本次報名動作無法完成！"
            }

        # 重建名單：優先從候補刪除，再從正取刪除
        # 正取部分（前 capacity 個）
        regular_part = current_list[:capacity]
        # 候補部分（capacity 開始）
        substitute_part = current_list[capacity:]

        # 在候補中刪除
        new_substitute = []
        deleted_from_sub = 0
        for name in substitute_part:
            if deleted_from_sub < abs(registration.num) and name and name.strip() == registration.name.strip():
                deleted_from_sub += 1
                continue
            new_substitute.append(name)

        remaining = abs(registration.num) - deleted_from_sub

        # 如果還需要刪除，從正取中刪除
        new_regular = []
        for name in regular_part:
            if remaining > 0 and name and name.strip() == registration.name.strip():
                remaining -= 1
                continue
            new_regular.append(name)

        # 合併：正取在前，候補在後
        new_list = new_regular + new_substitute

        # 補充正取空位
        while len(new_list) < capacity:
            new_list.append('')

        # 更新 Excel
        self.excel_service.update_excel(registration.date_str, registration.court, new_list, capacity=capacity)

        # 準備回覆（包含 Head 和 Tail）
        reply_message = self._format_reply(
            registration.date_str,
            registration.court,
            new_list,
            head=excel_data.get('head'),
            tail=excel_data.get('tail'),
            capacity=capacity
        )

        return {
            'success': True,
            'message': reply_message,
            'action': 'unsignup'
        }
    
    def _format_reply(self, date_str: str, court: str, name_list: list, head: list = None, tail: list = None, capacity: int = 24) -> str:
        """格式化回覆訊息"""
        court_name = self._get_court_name(court)

        # 計算正取和候補
        # capacity 由 caller 傳入，優先使用傳入值
        regular_names = [n for n in name_list[:capacity] if n]
        substitute_names = [n for n in name_list[capacity:] if n and n.startswith('候')]

        reply = ""

        # 加入 Head（如果有）
        if head:
            for line in head:
                reply += f"{line}\n"
            reply += "\n"

        # 報名名單標題
        #reply += f"📋 {date_str} {court_name} 報名名單\n\n"

        # 正取名單（完整序號 1~capacity，包含空白）
        reply += "【正取】\n"
        for i in range(capacity):
            name = name_list[i] if i < len(name_list) and name_list[i] else ""
            reply += f"{i+1}. {name}\n"

        # 候補名單
        #substitute_names = [n for n in name_list[capacity:] if n and n.startswith('候')]
        substitute_names = [n for n in name_list[capacity:] if n] 
        if substitute_names:
            reply += "\n【候補】\n"
            for i, name in enumerate(substitute_names, 1):
                reply += f"{i}. {name}\n"

        # 統計實際人數
        actual_regular = sum(1 for i in range(capacity) if i < len(name_list) and name_list[i])
        reply += f"\n共 {actual_regular} 正取，{len(substitute_names)} 候補\n"

        # 加入 Tail（如果有）
        if tail:
            for line in tail:
                reply += f"{line}\n"

        return reply
    
    def _get_court_name(self, court: str) -> str:
        """將 AM/PM 轉換為中文場次名稱"""
        return '上午場' if court == 'AM' else '下午場'
