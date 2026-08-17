import re
from enum import Enum
from typing import Dict, Any, Tuple

class IntentType(str, Enum):
    GREETING = "greeting"           # 日常問候與閒聊
    SYSTEM_CMD = "system_cmd"       # 系統指令（額度、說明、法規速查、兌換）
    QA_CONSULT = "qa_consult"       # 專業房產與法規問答諮詢（非發文，直接解答）
    GENERATE_HOOKS = "generate_hooks" # 專門產出爆款標題/鉤子
    GENERATE_POST = "generate_post"   # 爆款社群貼文/物件行銷生成

class IntentRouter:
    """
    LINE 訊息多意圖智能分流器
    精確區分：日常問候、系統指令、法規專業問答、標題鉤子創作、爆款社群發文
    """
    GREETING_WORDS = {
        "你好", "您好", "嗨", "哈囉", "安安", "在嗎", "早安", "午安", "晚安",
        "hi", "hello", "hey", "你好阿", "你好啊", "哈囉啊", "嗨嗨", "在麼", "在嘛",
        "謝謝", "感謝", "多謝", "thx", "thanks", "感恩"
    }

    SYSTEM_COMMANDS = {
        "說明": "help", "功能": "help", "help": "help", "menu": "help", "選單": "help",
        "額度": "quota", "次數": "quota", "查詢額度": "quota", "會員": "quota", "狀態": "quota",
        "法規": "policy", "政策": "policy", "限貸": "policy", "信用管制": "policy",
        "升級": "vip", "vip": "vip", "收費": "vip", "方案": "vip"
    }

    # 問答諮詢特徵詞（問句、法規查詢、疑問詞）
    QA_PATTERNS = [
        r"什麼是", r"何謂", r"怎麼算", r"如何算", r"多少[錢%趴成萬度]", r"可以.*嗎", r"能不能",
        r"限制是什麼", r"規定是什麼", r"有什麼影響", r"差在哪", r"比較", r"成數是多少",
        r"寬限期.*多久", r"資格是什麼", r"誰可以申請", r"罰則", r"合約問題", r"問一下", r"請問"
    ]

    # 產文關鍵字特徵
    POST_TRIGGER_WORDS = [
        "生成", "寫文案", "產文", "貼文", "發文", "寫物件", "文案", "reel", "threads",
        "短影音", "腳本", "爆款", "促銷", "買房攻略", "區域:", "總價:", "格局:"
    ]

    # 產鉤子特徵
    HOOK_TRIGGER_WORDS = ["寫鉤子", "產鉤子", "標題靈感", "想標題", "幫我想標題", "爆款標題", "5個標題"]

    @classmethod
    def classify_intent(cls, text: str) -> Tuple[IntentType, Dict[str, Any]]:
        raw = text.strip()
        clean = raw.lower().replace(" ", "").replace("！", "").replace("!", "").replace("～", "").replace("~", "").replace("？", "").replace("?", "").replace("，", "").replace(",", "")

        # 1. 兌換碼指令
        if raw.startswith("兌換") or raw.startswith("兌換碼") or raw.startswith("code"):
            return IntentType.SYSTEM_CMD, {"action": "redeem", "text": raw}

        # 2. 系統指令
        if clean in cls.SYSTEM_COMMANDS:
            return IntentType.SYSTEM_CMD, {"action": cls.SYSTEM_COMMANDS[clean], "text": raw}

        # 3. 日常打招呼與問候
        if clean in cls.GREETING_WORDS or (len(clean) <= 4 and clean in cls.GREETING_WORDS):
            return IntentType.GREETING, {"text": raw}

        # 4. 專門產出鉤子標題
        if any(k in raw.lower() for k in cls.HOOK_TRIGGER_WORDS):
            topic = raw
            for k in cls.HOOK_TRIGGER_WORDS:
                topic = topic.replace(k, "")
            return IntentType.GENERATE_HOOKS, {"topic": topic.strip() or "台灣最新買房避坑與房貸策略"}

        # 5. 明確的專業諮詢 / 法規問答（句尾有問號或包含問答詞彙）
        is_question = any(re.search(pat, raw) for pat in cls.QA_PATTERNS) or raw.endswith("？") or raw.endswith("?")
        has_post_intent = any(k in raw.lower() for k in cls.POST_TRIGGER_WORDS)

        if is_question and not has_post_intent:
            return IntentType.QA_CONSULT, {"question": raw}

        # 6. 極短無效輸入防呆
        re_keywords = ["房", "貸", "稅", "約", "買", "賣", "價", "案", "建", "坪", "公設", "都更", "危老", "租", "區", "樓", "地", "宅", "成", "利息", "重購", "裝修", "裝潢", "驗屋", "客變"]
        if len(raw) <= 2 and not any(k in raw.lower() for k in re_keywords):
            return IntentType.GREETING, {"text": raw, "fallback_short": True}

        # 7. 預設為社群貼文生成（清洗前綴指令詞，精確提取主題）
        clean_topic = raw
        for prefix in ["寫文案", "生成文案", "產文", "幫我寫", "文案:", "文案：", "貼文:", "貼文：", "主題:", "主題：", "我想要主題是:", "我想要主題是：", "我想要主題是"]:
            if clean_topic.startswith(prefix):
                clean_topic = clean_topic[len(prefix):].strip()
                break

        return IntentType.GENERATE_POST, {"topic": clean_topic or raw}
