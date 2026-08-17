import json
from typing import Dict, Any, Optional
from config import settings
from core.engine import ViralPostEngine
from core.quota_manager import QuotaManager
from core.intent_router import IntentRouter, IntentType

class LineBotHandler:
    """
    LINE Bot 訊息與多意圖路由處理器
    精確分流：日常問候、系統指令、法規專業問答、標題鉤子創作、爆款社群發文
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
        處理文字訊息並進行多意圖智能分流回覆
        """
        raw = text.strip()
        if not raw:
            return "您好！請輸入房市主題或指令（輸入「說明」可看完整功能）。"

        # 0. 執行意圖分類
        intent, meta = IntentRouter.classify_intent(raw)
        status = self.quota_manager.get_user_status(user_id)
        effective_key = api_key_override or settings.LINE_BOT_AI_API_KEY
        effective_provider = settings.LINE_BOT_AI_PROVIDER

        # ----------------------------------------------------
        # 意圖 1: 日常問候與閒聊（免扣額度）
        # ----------------------------------------------------
        if intent == IntentType.GREETING:
            if meta.get("fallback_short"):
                return "💡 請輸入更具體的房市主題或建案條件（例如：「新青安 3.0 額度」、「寫物件 區域:新莊 總價:1800萬」）。輸入「說明」可看完整功能！"
            
            return f"""👋 您好！我是房地產爆款發文與法規諮詢助手 🤖
（目前身份：{status['role']}，今日剩餘額度：{status['remaining_quota']}）

您可以直接傳送以下內容：
• 🎯 爆款發文：「新青安 3.0 首購自救攻略」
• 🏠 建案物件：「寫物件 區域:板橋 總價:2000萬 格局:3房」
• 🎬 短影音腳本：「Reels 腳本 買房避坑指南」
• ⚖️ 專業問答：「第二戶房貸成數最高多少？」
• 🎣 標題靈感：「寫鉤子 換屋策略」
• 📊 帳戶狀態：輸入「額度」"""

        # ----------------------------------------------------
        # 意圖 2: 系統指令（額度、說明、法規、VIP、兌換）（免扣額度）
        # ----------------------------------------------------
        if intent == IntentType.SYSTEM_CMD:
            action = meta.get("action")
            
            if action == "help":
                return f"""🤖 【房地產發文助手】指令清單：

📊 帳戶：{status['role']} (今日剩餘: {status['remaining_quota']})

1. 🎯 爆款社群發文：
   • 「寫文案 新青安 3.0 額度與排富」
   • 「寫物件 區域:新莊 總價:1880萬 格局:3房」
   • 「Reels 腳本 首購避坑」

2. ⚖️ 專業法規諮詢：
   • 直接提問，如：「新青安可以買預售屋嗎？」、「第二戶房貸限制是什麼？」

3. 🎣 爆款標題靈感：
   • 「寫鉤子 房貸成數」或輸入「鉤子」抽 3 組

4. 🎟️ 帳戶與會員：
   • 「額度」：查詢今日剩餘次數
   • 「兌換 VIP888」：解鎖永久 VIP 無限產文"""

            if action == "quota":
                return f"""📊 【您的帳戶額度報告】：
• 用戶 ID：{user_id}
• 會員身份：{status['role']}
• 今日剩餘額度：{status['remaining_quota']}
• 累計已生成：{status['total_used']} 篇

🎁 體驗福利：輸入「兌換 VIP888」立即升級為永久 VIP 會員！"""

            if action == "vip":
                return """💎 【VIP 會員方案說明】：

• 免費方案：每日 3 次爆款產文（每日午夜自動重置）
• VIP 尊爵方案：永久無限次產文 + 最新政策即時同步

🎉 測試期間限時免費升級：
直接於聊天室輸入「兌換 VIP888」即可立即解鎖！"""

            if action == "policy":
                policies = self.engine.validator.policies
                reply = ["📌 【台灣房市最新法規與預告草案速查】：\n"]
                for p in policies[:3]:
                    reply.append(f"🔹 {p.get('title')}（{p.get('status')}）")
                    for r in p.get("key_rules", [])[:2]:
                        reply.append(f"  • {r}")
                    if p.get("warning_notice"):
                        reply.append(f"  ⚠️ {p.get('warning_notice')}")
                    reply.append("")
                reply.append("💡 輸入具體問題可直接為您進行專業法規解答。")
                return "\n".join(reply)

            if action == "redeem":
                parts = raw.replace("：", ":").replace("碼", " ").split()
                code = parts[-1] if len(parts) > 1 else ""
                if not code:
                    return "請輸入完整兌換指令，例如：「兌換 VIP888」。"
                res = self.quota_manager.redeem_code(user_id, code)
                return res["message"]

        # ----------------------------------------------------
        # 意圖 3: 專門產出爆款標題與鉤子（免扣或獨立處理）
        # ----------------------------------------------------
        if intent == IntentType.GENERATE_HOOKS:
            topic = meta.get("topic", "台灣最新買房避坑與房貸策略")
            hooks = self.engine.generate_dynamic_hooks(
                topic=topic,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            reply = [f"🎣 【為您量身打造的 5 組「{topic}」爆款開頭鉤子】：\n"]
            for i, h in enumerate(hooks, 1):
                reply.append(f"{i}. {h}")
            reply.append("\n💡 複製任一標題並傳送「以此寫文案」即可生成完整貼文！")
            return "\n".join(reply)

        # ----------------------------------------------------
        # 意圖 4: 專業房產與法規諮詢問答 (Q&A 模式，直接條列解答)
        # ----------------------------------------------------
        if intent == IntentType.QA_CONSULT:
            question = meta.get("question", raw)
            ans = self.engine.answer_consulting_question(
                question=question,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            return ans

        # ----------------------------------------------------
        # 意圖 5: 爆款社群貼文 / 物件行銷生成 (消耗額度)
        # ----------------------------------------------------
        quota_check = self.quota_manager.check_and_consume_quota(user_id)
        if not quota_check["allowed"]:
            return """⚠️ 【今日免費額度已用完】

您今日的 3 次免費產文額度已用盡。
• 每日 00:00 自動恢復 3 次免費額度
• 🎁 限時福利：輸入「兌換 VIP888」立即升級為 VIP 永久無限產文！"""

        # 解析目標社群平台（預設為 Threads 爆款短文格式）
        platform = "threads"
        tone = "辛辣直白一針見血、撕扯痛點、大白話揭露市場真相"
        raw_lower = raw.lower()
        if any(k in raw_lower for k in ["reels", "短影音", "腳本", "短片", "影片", "tiktok"]):
            platform = "reels"
        elif any(k in raw_lower for k in ["ig", "instagram", "圖文", "卡片"]):
            platform = "instagram"
        elif any(k in raw_lower for k in ["fb", "facebook", "長文", "深度"]):
            platform = "facebook"
        elif "line" in raw_lower:
            platform = "line"

        # 解析物件行銷參數
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

        if not effective_key:
            return "❌ LINE 機器人服務尚未配置 AI 金鑰！請通知系統管理員於伺服器 .env 填入 LINE_BOT_AI_API_KEY。"

        result = self.engine.generate(
            topic=raw,
            platform=platform,
            tone=tone,
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
