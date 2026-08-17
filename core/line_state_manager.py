import json
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class LineUserState(str, Enum):
    IDLE = "idle"                             # 初始/主選單狀態
    WAITING_POST_TOPIC = "waiting_post_topic" # 等待輸入發文主題
    WAITING_PROPERTY_INFO = "waiting_prop"    # 等待輸入物件資訊
    WAITING_QA_QUESTION = "waiting_qa"        # 等待輸入法規諮詢問題
    WAITING_HOOK_TOPIC = "waiting_hook_topic" # 等待輸入鉤子標題主題

class LineStateManager:
    """
    LINE 用戶對話狀態管理器（支援狀態持久化與多用戶隔離）
    """
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.state_file = data_dir / "line_user_states.json"
        self.states: Dict[str, Dict[str, Any]] = self._load_states()

    def _load_states(self) -> Dict[str, Dict[str, Any]]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_states(self):
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.states, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LineStateManager] 狀態儲存異常: {e}")

    def get_state(self, user_id: str) -> LineUserState:
        user_data = self.states.get(user_id, {})
        state_str = user_data.get("state", LineUserState.IDLE.value)
        try:
            return LineUserState(state_str)
        except ValueError:
            return LineUserState.IDLE

    def set_state(self, user_id: str, state: LineUserState, context: Optional[Dict[str, Any]] = None):
        self.states[user_id] = {
            "state": state.value,
            "context": context or {},
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_states()

    def reset_state(self, user_id: str):
        self.set_state(user_id, LineUserState.IDLE)
