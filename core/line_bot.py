import json
from typing import Dict, Any, Optional
from pathlib import Path
from config import settings
from core.engine import ViralPostEngine
from core.quota_manager import QuotaManager
from core.line_state_manager import LineStateManager, LineUserState

class LineBotHandler:
    """
    LINE Bot 2 步引導式對話處理器
    實作清晰的 Step-by-Step 模式：選功能 (1~5) ➔ 輸入主題/條件 ➔ 即時產出
    """
    def __init__(self, engine: ViralPostEngine):
        self.engine = engine
        self.channel_secret = settings.LINE_CHANNEL_SECRET
        self.channel_access_token = settings.LINE_CHANNEL_ACCESS_TOKEN
        self.quota_manager = QuotaManager(settings.DATA_DIR)
        self.state_manager = LineStateManager(settings.DATA_DIR)

    def _render_main_menu(self, user_id: str, tip: str = "") -> str:
        """產生主選單"""
        status = self.quota_manager.get_user_status(user_id)
        menu = [
            f"👋 您好！我是房地產發文與法規諮詢助手 🤖",
            f"📊 帳戶：{status['role']} (今日剩餘額度: {status['remaining_quota']})\n",
            "請回覆【數字代號】選擇您需要的服務：\n",
            "1️⃣ 爆款社群發文（Threads 辛辣直白短文）",
            "2️⃣ 房屋物件行銷（精準鎖定買方成交文案）",
            "3️⃣ 房產法規諮詢（法規/稅制/房貸 Q&A 解答）",
            "4️⃣ 爆款標題靈感（量身創作 5 組吸睛開頭）",
            "5️⃣ 帳戶額度查詢與 VIP 升級\n",
            "💡 隨時回覆「0」可返回此主選單。"
        ]
        if tip:
            menu.insert(0, f"💡 {tip}\n")
        return "\n".join(menu)

    def handle_message_text(
        self,
        text: str,
        user_id: str = "mock_user_default",
        api_key_override: Optional[str] = None
    ) -> str:
        """
        以 2 步引導狀態機處理使用者輸入
        """
        raw = text.strip()
        if not raw:
            return self._render_main_menu(user_id)

        effective_key = api_key_override or settings.LINE_BOT_AI_API_KEY
        effective_provider = settings.LINE_BOT_AI_PROVIDER

        # ---------------------------------------------------------
        # 全域指令 1: 返回主選單 / 取消
        # ---------------------------------------------------------
        if raw in ["0", "取消", "返回", "選單", "主選單", "menu", "help", "說明", "你好", "嗨", "哈囉", "早安", "晚安", "在嗎", "hi", "hello"]:
            self.state_manager.reset_state(user_id)
            return self._render_main_menu(user_id)

        # ---------------------------------------------------------
        # 全域指令 2: 兌換碼啟動 VIP
        # ---------------------------------------------------------
        if raw.startswith("兌換") or raw.startswith("兌換碼") or raw.startswith("code"):
            parts = raw.replace("：", ":").replace("碼", " ").split()
            code = parts[-1] if len(parts) > 1 else ""
            if not code:
                return "請輸入完整兌換指令，例如：「兌換 VIP888」。"
            res = self.quota_manager.redeem_code(user_id, code)
            return f"{res['message']}\n\n" + self._render_main_menu(user_id)

        # 取得用戶當前對話狀態
        current_state = self.state_manager.get_state(user_id)

        # =========================================================
        # 狀態 A: IDLE (主選單狀態，等待使用者輸入 1~5 選擇功能)
        # =========================================================
        if current_state == LineUserState.IDLE:
            # 選擇 1: 爆款社群發文
            if raw in ["1", "1️⃣", "發文", "寫文案", "社群發文", "貼文"]:
                self.state_manager.set_state(user_id, LineUserState.WAITING_POST_TOPIC)
                return """✍️ 【步驟 2/2：爆款社群發文模式】

請直接輸入您想探討的「房市主題」：
（例如：裝修須知、換屋自救攻略、新青安3.0避坑、第七波信用管制解方）

💡 系統將自動為您生成 Threads 辛辣一針見血短文。
🔙 回覆「0」可隨時返回主選單。"""

            # 選擇 2: 房屋物件行銷
            if raw in ["2", "2️⃣", "物件", "賣房", "物件行銷", "房屋行銷", "房屋"]:
                self.state_manager.set_state(user_id, LineUserState.WAITING_PROPERTY_INFO)
                return """🏢 【步驟 2/2：房屋物件行銷模式】

請輸入您的房屋物件資訊，可包含「區域、總價、格局、案名、賣點」：
範例：新北新莊副都心 指標美邸 總價1880萬 3房 近捷運超大棟距

🔙 回覆「0」可隨時返回主選單。"""

            # 選擇 3: 房產法規諮詢
            if raw in ["3", "3️⃣", "法規", "諮詢", "問答", "法規諮詢", "房貸"]:
                self.state_manager.set_state(user_id, LineUserState.WAITING_QA_QUESTION)
                return """⚖️ 【步驟 2/2：房產法規與稅制諮詢模式】

請直接輸入您想諮詢的具體疑問：
（例如：第二戶房貸最高可以貸幾成？新青安能買預售屋嗎？囤房稅2.0稅率多少？）

💡 AI 房產顧問將直接給出清晰條列解答與實戰避坑建議。
🔙 回覆「0」可隨時返回主選單。"""

            # 選擇 4: 爆款開頭標題靈感
            if raw in ["4", "4️⃣", "鉤子", "標題", "爆款標題", "標題靈感", "hook"]:
                self.state_manager.set_state(user_id, LineUserState.WAITING_HOOK_TOPIC)
                return """🎣 【步驟 2/2：爆款開頭標題靈感模式】

請輸入您想創作標題的主題：
（例如：換屋自備款、首購看屋陷阱、中古屋裝修預算）

💡 AI 將針對該主題為您量身產出 5 組吸睛開頭金句。
🔙 回覆「0」可隨時返回主選單。"""

            # 選擇 5: 帳戶額度與 VIP 服務
            if raw in ["5", "5️⃣", "額度", "查詢額度", "會員", "vip", "升級", "次數"]:
                status = self.quota_manager.get_user_status(user_id)
                return f"""📊 【您的帳戶額度報告】：
• 用戶 ID：{user_id}
• 會員身份：{status['role']}
• 今日剩餘額度：{status['remaining_quota']}
• 累計已生成：{status['total_used']} 篇

💎 【VIP 會員權益】：
• 免費會員：每日 3 次生成額度（每日 00:00 重置）
• VIP 尊爵：永久無限次產文 + 最新政策即時同步

🎉 體驗福利：輸入「兌換 VIP888」立即升級為永久 VIP！

🔙 回覆「0」可返回主選單。"""

            # 若使用者在主選單輸入了非 1~5 的文字，親切提示重新選擇
            return self._render_main_menu(user_id, tip=f"收到「{raw}」，請先回覆數字 1~5 選擇您要使用的功能：")

        # =========================================================
        # 狀態 B: WAITING_POST_TOPIC (模式 1：生成社群發文)
        # =========================================================
        if current_state == LineUserState.WAITING_POST_TOPIC:
            quota_check = self.quota_manager.check_and_consume_quota(user_id)
            if not quota_check["allowed"]:
                self.state_manager.reset_state(user_id)
                return """⚠️ 【今日免費額度已用完】

您今日的 3 次免費產文額度已用盡。
• 每日 00:00 自動恢復 3 次免費額度
• 🎁 限時福利：輸入「兌換 VIP888」立即升級為 VIP 永久無限產文！

🔙 回覆「0」可返回主選單。"""

            if not effective_key:
                self.state_manager.reset_state(user_id)
                return "❌ LINE 機器人服務尚未配置 AI 金鑰！請通知系統管理員於伺服器 .env 填入 LINE_BOT_AI_API_KEY。"

            # 執行 Threads 爆款短文生成
            result = self.engine.generate(
                topic=raw,
                platform="threads",
                tone="辛辣直白一針見血、撕扯痛點、大白話揭露市場真相",
                property_data=None,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            self.state_manager.reset_state(user_id)

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
            reply.append("💡 回覆「0」可隨時回到主選單。")
            return "\n".join(reply)

        # =========================================================
        # 狀態 C: WAITING_PROPERTY_INFO (模式 2：生成物件行銷文案)
        # =========================================================
        if current_state == LineUserState.WAITING_PROPERTY_INFO:
            quota_check = self.quota_manager.check_and_consume_quota(user_id)
            if not quota_check["allowed"]:
                self.state_manager.reset_state(user_id)
                return """⚠️ 【今日免費額度已用完】

您今日的 3 次免費產文額度已用盡。
• 每日 00:00 自動恢復 3 次免費額度
• 🎁 限時福利：輸入「兌換 VIP888」立即升級為 VIP 永久無限產文！

🔙 回覆「0」可返回主選單。"""

            if not effective_key:
                self.state_manager.reset_state(user_id)
                return "❌ LINE 機器人服務尚未配置 AI 金鑰！請通知系統管理員於伺服器 .env 填入 LINE_BOT_AI_API_KEY。"

            # 解析物件欄位
            property_data = {}
            for part in raw.replace("：", ":").split():
                if ":" in part:
                    k, v = part.split(":", 1)
                    if "區" in k: property_data["region"] = v
                    elif "總價" in k or "價" in k: property_data["price"] = v
                    elif "格局" in k or "房" in k: property_data["layout"] = v
                    elif "案名" in k or "社區" in k: property_data["title"] = v
                    elif "賣點" in k: property_data["highlights"] = v

            if not property_data:
                property_data = {"highlights": raw}

            result = self.engine.generate(
                topic=raw,
                platform="threads",
                tone="辛辣直白一針見血、撕扯痛點、大白話揭露市場真相",
                property_data=property_data,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            self.state_manager.reset_state(user_id)

            if not result.get("success"):
                return result.get("error", "❌ AI 生成失敗，請確認 API Key 設定。")

            content = result.get("content", "")
            reply = [
                content,
                f"\n--------------------\n📊 帳戶：{quota_check['role'].upper()} | 今日剩餘額度：{quota_check['remaining']}",
                "💡 回覆「0」可隨時回到主選單。"
            ]
            return "\n".join(reply)

        # =========================================================
        # 狀態 D: WAITING_QA_QUESTION (模式 3：專業法規諮詢)
        # =========================================================
        if current_state == LineUserState.WAITING_QA_QUESTION:
            ans = self.engine.answer_consulting_question(
                question=raw,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            self.state_manager.reset_state(user_id)
            return f"{ans}\n\n💡 回覆「0」可隨時回到主選單。"

        # =========================================================
        # 狀態 E: WAITING_HOOK_TOPIC (模式 4：爆款標題靈感)
        # =========================================================
        if current_state == LineUserState.WAITING_HOOK_TOPIC:
            hooks = self.engine.generate_dynamic_hooks(
                topic=raw,
                api_key_override=effective_key,
                provider_override=effective_provider
            )
            self.state_manager.reset_state(user_id)
            reply = [f"🎣 【為您量身打造的 5 組「{raw}」爆款開頭鉤子】：\n"]
            for i, h in enumerate(hooks, 1):
                reply.append(f"{i}. {h}")
            reply.append("\n💡 複製任一標題回覆「1」可直接發文，或回覆「0」返回主選單。")
            return "\n".join(reply)

        # Fallback
        self.state_manager.reset_state(user_id)
        return self._render_main_menu(user_id)
