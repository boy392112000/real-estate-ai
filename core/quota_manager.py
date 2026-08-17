import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class QuotaManager:
    """
    LINE 用戶配額與 VIP 會員管理引擎
    支援每日免費配額、每日午夜自動重置、兌換碼解鎖與本地持久化帳本
    """
    DEFAULT_DAILY_FREE_QUOTA = 3

    REDEEM_CODES = {
        "VIP888": {"role": "vip", "quota": 9999, "desc": "永久 VIP 無限產文會員"},
        "PRO2026": {"role": "vip", "quota": 9999, "desc": "2026 專業操盤手專案會員"},
        "BONUS10": {"role": "free", "add_quota": 10, "desc": "加贈 10 次產文額度"}
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.ledger_path = self.data_dir / "line_user_quota.json"
        self.ledger: Dict[str, Any] = self._load_ledger()

    def _load_ledger(self) -> Dict[str, Any]:
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_ledger(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.ledger, f, ensure_ascii=False, indent=2)

    def _get_or_create_user(self, user_id: str) -> Dict[str, Any]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if user_id not in self.ledger:
            self.ledger[user_id] = {
                "role": "free",
                "remaining_quota": self.DEFAULT_DAILY_FREE_QUOTA,
                "total_used": 0,
                "last_reset_date": today_str,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_ledger()
            return self.ledger[user_id]

        user = self.ledger[user_id]
        # 若跨日且為免費會員，自動重置每日免費額度
        if user.get("role") == "free" and user.get("last_reset_date") != today_str:
            user["remaining_quota"] = self.DEFAULT_DAILY_FREE_QUOTA
            user["last_reset_date"] = today_str
            self._save_ledger()

        return user

    def check_and_consume_quota(self, user_id: str) -> Dict[str, Any]:
        """
        檢核並扣除 1 次額度
        """
        user = self._get_or_create_user(user_id)
        role = user.get("role", "free")

        if role == "vip":
            user["total_used"] = user.get("total_used", 0) + 1
            self._save_ledger()
            return {
                "allowed": True,
                "role": "vip",
                "remaining": "無限次",
                "total_used": user["total_used"],
                "message": "VIP 會員尊爵使用中"
            }

        remaining = user.get("remaining_quota", 0)
        if remaining <= 0:
            return {
                "allowed": False,
                "role": "free",
                "remaining": 0,
                "total_used": user.get("total_used", 0),
                "message": "今日免費 3 次額度已用完，請輸入【兌換碼】或聯繫官方升級 VIP！"
            }

        user["remaining_quota"] = remaining - 1
        user["total_used"] = user.get("total_used", 0) + 1
        self._save_ledger()

        return {
            "allowed": True,
            "role": "free",
            "remaining": user["remaining_quota"],
            "total_used": user["total_used"],
            "message": f"今日剩餘免費額度：{user['remaining_quota']} 次"
        }

    def redeem_code(self, user_id: str, code: str) -> Dict[str, Any]:
        """
        兌換禮券碼 / VIP 啟動碼
        """
        clean_code = code.strip().upper()
        if clean_code not in self.REDEEM_CODES:
            return {"success": False, "message": "❌ 兌換碼無效或已過期，請確認輸入是否正確。"}

        info = self.REDEEM_CODES[clean_code]
        user = self._get_or_create_user(user_id)

        if info.get("role") == "vip":
            user["role"] = "vip"
            user["vip_activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "add_quota" in info:
            user["remaining_quota"] = user.get("remaining_quota", 0) + info["add_quota"]

        self._save_ledger()
        return {
            "success": True,
            "role": user.get("role"),
            "remaining": "無限次" if user.get("role") == "vip" else user.get("remaining_quota"),
            "message": f"🎉 恭喜！已成功啟用【{info['desc']}】！"
        }

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        user = self._get_or_create_user(user_id)
        is_vip = user.get("role") == "vip"
        return {
            "user_id": user_id,
            "role": "VIP 會員" if is_vip else "免費會員",
            "is_vip": is_vip,
            "remaining_quota": "無限次" if is_vip else f"{user.get('remaining_quota', 0)} 次",
            "total_used": user.get("total_used", 0)
        }
