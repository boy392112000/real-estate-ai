import json
from typing import Dict, Any, Optional
from config import settings
from core.engine import ViralPostEngine
from core.quota_manager import QuotaManager

class LineBotHandler:
    """
    LINE Bot 訊息與商業化配額處理器
    支援用戶額度檢核、VIP 兌換碼啟動、多平台格式解析與法規速查
    """
    def __init__(self, engine: ViralPostEngine):
        self.engine = engine
        self.channel_secret = settings.LINE_CHANNEL_SECRET
        self.channel_access_token = settings.LINE_CHANNEL_ACCESS_TOKEN
        self.quota_manager = QuotaManager(settings.DATA_DIR)

    def handle_message_text(
        self,
        text: str,
        user_id: str = "mock_user_default",
        api_key_override: Optional[str] = None
    ) -> str:
        """
        處理文字訊息並產生回覆內容（支援用戶隔離與額度管控）
        """
        raw = text.strip()

        # 0. 日常問候與打招呼（免扣額度，親切引導）
        greetings = ["你好", "您好", "嗨", "哈囉", "安安", "在嗎", "早安", "午安", "晚安", "hi", "hello", "hey", "你好阿", "你好啊", "哈囉啊", "嗨嗨", "在麼", "在嘛"]
        clean_greeting = raw.lower().replace(" ", "").replace("！", "").replace("!", "").replace("～", "").replace("~", "").replace("？", "").replace("?", "").replace("，", "").replace(",", "")
        if clean_greeting in greetings or any(clean_greeting == g for g in greetings):
            status = self.quota_manager.get_user_status(user_id)
            return f"""👋 您好！我是房地產爆款發文助手 🤖
（目前身份：{status['role']}，今日剩餘額度：{status['remaining_quota']}）

想產出什麼房市主題或建案文案呢？直接傳送給我即可：
• 🎯 房市政策：「新青安 3.0 首購解方」
• 🏠 建案物件：「寫物件 區域:板橋 總價:2000萬 格局:3房」
• 🎬 短影音：「Reels 腳本 買房避坑指南」
• 📜 法規速查：輸入「法規」
• 📊 帳戶狀態：輸入「額度」"""

        # 0.1 過短無效字詞防呆（< 3 字且無房產關鍵字，免扣額度）
        re_keywords = ["房", "貸", "稅", "約", "買", "賣", "價", "案", "建", "坪", "公設", "都更", "危老", "租", "區", "樓", "地", "宅", "成", "利息", "重購", "hook", "鉤子", "說明", "功能", "額度", "vip", "兌換"]
        if len(raw) <= 2 and not any(k in raw.lower() for k in re_keywords):
            return "💡 請輸入更具體的房市主題或建案條件（例如：「第七波信用管制解方」、「寫物件 區域:新莊 總價:1800萬」）。輸入「說明」可看完整指令！"

        # 1. 幫助與功能說明
        if raw in ["說明", "功能", "help", "menu", "選單"]:
            status = self.quota_manager.get_user_status(user_id)
            return f"""🤖 【房地產爆款發文機器人】

📊 當前帳戶：{status['role']} (今日剩餘: {status['remaining_quota']})

1. 🎯 快速生成爆款文案：
   • 「生成文案 主題：新青安 3.0 額度與排富」
   • 「寫物件 區域：新莊 總價：1880萬 格局：3房」

2. 📜 台灣最新法規速查：
   • 輸入「法規」或「限貸」查看最新政策。

3. 🎟️ 額度與會員服務：
   • 輸入「額度」：查詢今日剩餘次數。
   • 輸入「兌換 VIP888」：解鎖永久 VIP 無限產文。
   • 輸入「鉤子」：隨機抽 3 組社群吸睛標題。"""

        # 2. 查詢額度與會員狀態
        if raw in ["額度", "次數", "查詢額度", "會員", "狀態"]:
            status = self.quota_manager.get_user_status(user_id)
            return f"""📊 【您的帳戶額度報告】：
• 用戶 ID：{user_id}
• 會員身份：{status['role']}
• 今日剩餘額度：{status['remaining_quota']}
• 累計已生成：{status['total_used']} 篇

🎁 體驗福利：輸入「兌換 VIP888」立即升級為永久 VIP 會員！"""

        # 3. 兌換碼啟動機制
        if raw.startswith("兌換") or raw.startswith("兌換碼") or raw.startswith("code"):
            parts = raw.replace("：", ":").replace("碼", " ").split()
            code = parts[-1] if len(parts) > 1 else ""
            if not code:
                return "請輸入完整兌換指令，例如：「兌換 VIP888」。"
            res = self.quota_manager.redeem_code(user_id, code)
            return res["message"]

        # 4. VIP 升級與收費說明
        if raw in ["升級", "vip", "收費", "方案", "購買"]:
            return """💎 【VIP 會員方案說明】：

• 免費方案：每日 3 次爆款產文（每日午夜自動重置）
• VIP 尊爵方案：永久無限次產文 + 最新政策即時同步

🎉 測試期間限時免費升級：
直接於聊天室輸入「兌換 VIP888」即可立即解鎖！"""

        # 5. 最新法規速查
        if raw in ["法規", "政策", "限貸", "信用管制"]:
            policies = self.engine.validator.policies
            reply = ["📌 【台灣房市最新法規與預告草案速查】：\n"]
            for p in policies[:3]:
                reply.append(f"🔹 {p.get('title')}（{p.get('status')}）")
                for r in p.get("key_rules", [])[:2]:
                    reply.append(f"  • {r}")
                if p.get("warning_notice"):
                    reply.append(f"  ⚠️ {p.get('warning_notice')}")
                reply.append("")
            reply.append("💡 輸入主題即可生成針對性深度避坑長文。")
            return "\n".join(reply)

        # 6. 隨機鉤子庫
        if raw in ["鉤子", "標題", "hook"]:
            hooks = self.engine.get_random_hooks(count=3)
            reply = ["🎣 【精選房產爆款鉤子標題】：\n"]
            for i, h in enumerate(hooks, 1):
                reply.append(f"{i}. {h}")
            reply.append("\n💡 複製任一標題並加上「以此標題寫文案」即可生成！")
            return "\n".join(reply)

        # 7. 額度檢核與扣點（生成文章前攔截）
        quota_check = self.quota_manager.check_and_consume_quota(user_id)
        if not quota_check["allowed"]:
            return """⚠️ 【今日免費額度已用完】

您今日的 3 次免費產文額度已用盡。
• 每日 00:00 自動恢復 3 次免費額度
• 🎁 限時福利：輸入「兌換 VIP888」立即升級為 VIP 永久無限產文！"""

        # 8. 解析物件參數或主題產文（針對手機用戶預設為 IG/Threads/Reels 節奏）
        platform = "instagram"
        raw_lower = raw.lower()
        if any(k in raw_lower for k in ["reels", "短影音", "腳本", "短片", "影片", "tiktok"]):
            platform = "reels"
        elif any(k in raw_lower for k in ["threads", "脆", "短金句", "短文"]):
            platform = "threads"
        elif any(k in raw_lower for k in ["fb", "facebook", "長文", "深度"]):
            platform = "facebook"
        elif "line" in raw_lower:
            platform = "line"

        # 檢查是否有物件參數關鍵字
        property_data = None
        if any(k in raw for k in ["區域", "總價", "格局", "坪數", "案名"]):
            property_data = {}
            for part in raw.replace("：", ":").split():
                if ":" in part:
                    k, v = part.split(":", 1)
                    if "區" in k: property_data["region"] = v
                    elif "總價" in k or "價" in k: property_data["price"] = v
                    elif "格局" in k or "房" in k: property_data["layout"] = v
                    elif "案名" in k or "社區" in k: property_data["title"] = v
                    elif "賣點" in k: property_data["highlights"] = v

        # 決定 LINE Bot 調用之 AI 金鑰與模型 (優先使用傳入的 override，若無則使用 .env 中的 LINE_BOT_AI_API_KEY)
        effective_key = api_key_override or settings.LINE_BOT_AI_API_KEY
        effective_provider = settings.LINE_BOT_AI_PROVIDER

        if not effective_key:
            return "❌ LINE 機器人服務尚未配置 AI 金鑰！請通知系統管理員於伺服器 .env 填入 LINE_BOT_AI_API_KEY。"

        result = self.engine.generate(
            topic=raw,
            platform=platform,
            property_data=property_data,
            api_key_override=effective_key,
            provider_override=effective_provider
        )

        if not result.get("success"):
            return result.get("error", "❌ AI 生成失敗，請確認 API Key 設定。")

        content = result.get("content", "")
        validation = result.get("validation", {})
        
        reply = [content]
        if validation and validation.get("warnings"):
            reply.append("\n⚠️ 【法規事實檢核提醒】：")
            for w in validation.get("warnings"):
                reply.append(f"- {w}")

        reply.append(f"\n--------------------\n📊 帳戶：{quota_check['role'].upper()} | 今日剩餘額度：{quota_check['remaining']}")
        return "\n".join(reply)
