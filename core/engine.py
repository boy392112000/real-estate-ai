import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from config import settings
from core.validator import PolicyValidator
from core.web_search import RealTimePolicyFetcher

class ViralPostEngine:
    """
    房地產爆款發文生成核心引擎
    整合 50+ 鉤子庫、即時聯網資訊比對、台灣最新法規 Grounding 注入、多平台格式排版與反幻覺驗證
    """
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.validator = PolicyValidator(knowledge_dir)
        self.live_fetcher = RealTimePolicyFetcher()
        self.hooks_data = self._load_hooks()

    def _load_hooks(self) -> Dict[str, Any]:
        path = self.knowledge_dir / "viral_hooks.json"
        if not path.exists() or path.stat().st_size == 0:
            fallback = self.knowledge_dir.parent / "default_knowledge" / "viral_hooks.json"
            if fallback.exists():
                path = fallback
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Engine] 載入鉤子庫失敗: {e}")
        return {"categories": []}

    def get_hook_categories(self) -> List[Dict[str, Any]]:
        return self.hooks_data.get("categories", [])

    def get_hooks(self, category_id: str = "") -> List[str]:
        """按順序返回知識庫中的範例標題，絕不隨機亂抽"""
        categories = self.hooks_data.get("categories", [])
        pool = []
        for cat in categories:
            if not category_id or cat.get("id") == category_id:
                pool.extend(cat.get("hooks", []))
        if not pool:
            return ["買房這條路上，最貴的成本從來不是房價，而是『猶豫不決』。"]
        return pool

    def generate_dynamic_hooks(
        self,
        topic: str = "",
        category_id: str = "policy_pitfall",
        property_data: Optional[Dict[str, Any]] = None,
        api_key_override: Optional[str] = None,
        provider_override: Optional[str] = None
    ) -> List[str]:
        """
        利用 AI 依據特定主題或物件即時客製化產出 5 組專屬高爆發力開頭鉤子 (Hook)
        """
        provider = provider_override or "gemini"
        gemini_key = api_key_override if provider == "gemini" else None
        openai_key = api_key_override if provider == "openai" else None

        target_topic = topic.strip() if topic else "台灣最新買房避坑與房貸策略"
        if property_data and property_data.get("title"):
            target_topic += f"（物件：{property_data.get('region', '')} {property_data.get('title', '')}，總價 {property_data.get('price', '')}）"

        prompt = f"""
你是一位台灣頂級房產社群爆款操盤手。請針對以下【主題/物件】：
「{target_topic}」

為我撰寫 5 組極具社群點擊率、撕扯痛點、引發好奇心與爭議的「開頭第一句話鉤子（Hooks）」。

要求：
1. 每組僅 1 句話（20~45 字），適合 Facebook/Threads 第一行。
2. 善用數字對比、急迫感、顛覆常理、政策避坑或扎心情感。
3. 繁體中文，格式為每行一組，不要包含編號或廢話。
"""

        # 優先呼叫 LLM
        if provider == "gemini" and gemini_key:
            try:
                import requests
                for m in ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 2048,
                            "thinkingConfig": {"thinkingBudget": 0}
                        }
                    }
                    res = requests.post(url, json=payload, timeout=15)
                    if res.status_code == 200:
                        candidates = res.json().get("candidates", [])
                        if candidates:
                            raw_parts = candidates[0].get("content", {}).get("parts", [])
                            full_text = "".join([p.get("text", "") for p in raw_parts if "text" in p and not p.get("thought", False)])
                            lines = [l.strip().lstrip("12345. -*•") for l in full_text.split("\n") if l.strip()]
                            if len(lines) >= 3:
                                return lines[:5]
            except Exception as e:
                print(f"[Engine] Gemini 產生鉤子異常: {e}")

        elif provider == "openai" and openai_key:
            try:
                import requests
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=15)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"]
                    lines = [l.strip().lstrip("12345. -*•") for l in text.split("\n") if l.strip()]
                    if len(lines) >= 3:
                        return lines[:5]
            except Exception as e:
                print(f"[Engine] OpenAI 產生鉤子異常: {e}")

        # 智慧動態公式庫 (AI 離線時依主題動態組合)
        return [
            f"千萬別等到簽約才問貸款！關於【{target_topic}】，這 3 個致命雷區讓一堆人直接斷頭...",
            f"大家都以為【{target_topic}】穩賺不賠？算完這筆 30 年真實帳本，結論打臉所有人！",
            f"為什麼懂買的資深投資客，都在偷偷研究【{target_topic}】？關鍵在於這項隱藏新規...",
            f"房仲絕對不會主動告訴你的秘密：面對【{target_topic}】，這樣談判自備款直接省下一半！",
            f"如果你今年正打算看房，請把這篇關於【{target_topic}】的避坑指南讀完再出門！"
        ]

    def answer_consulting_question(
        self,
        question: str,
        api_key_override: Optional[str] = None,
        provider_override: Optional[str] = None
    ) -> str:
        """
        專業房產法規與稅制諮詢問答 (非行銷文案，直接清晰條列解答)
        """
        provider = provider_override or "gemini"
        key = api_key_override

        # 檢索本地法規與聯網最新資訊
        grounding = self.validator.get_grounding_context(question)
        live_data = self.live_fetcher.build_live_grounding_context(question)
        full_context = f"{grounding}\n\n{live_data.get('context_text', '')}"

        prompt = f"""
你是一位台灣頂級房地產法規與稅務資深顧問。請針對使用者的諮詢問題，給出最權威、清晰、條列化的專業解答。

【使用者問題】：
{question}

【台灣最新官方政策與法規依據（請嚴格遵循，禁止幻覺）】：
{full_context}

【回答要求】：
1. 第一行直接給出核心結論（可以/不行/成數/稅率）。
2. 條列說明法規關鍵細節與適用條件（附帶主管機關或專有名詞）。
3. 提示 1~2 點自住或投資實務上的「避坑注意事項」。
4. 繁體中文，語氣客觀專業且親切，篇幅約 250~450 字，禁止輸出社群發文的宣傳行銷詞彙。
"""
        if provider == "gemini" and key:
            try:
                import requests
                for m in ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 4096,
                            "thinkingConfig": {"thinkingBudget": 0}
                        }
                    }
                    res = requests.post(url, json=payload, timeout=25)
                    if res.status_code == 200:
                        candidates = res.json().get("candidates", [])
                        if candidates:
                            raw_parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join([p.get("text", "") for p in raw_parts if "text" in p and not p.get("thought", False)]).strip()
                            if text:
                                return f"🏛️ 【房產顧問專業解答】：\n\n{text}"
            except Exception as e:
                print(f"[Engine] Gemini 諮詢問答異常: {e}")

        elif provider == "openai" and key:
            try:
                import requests
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是一位頂級台灣房地產法規與稅務資深顧問。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048
                }
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"].strip()
                    if text:
                        return f"🏛️ 【房產顧問專業解答】：\n\n{text}"
            except Exception as e:
                print(f"[Engine] OpenAI 諮詢問答異常: {e}")

        return f"🏛️ 【房產法規速查】：\n針對您詢問的「{question}」，相關法規要點如下：\n{grounding}\n\n💡 如需深度宣傳文案請輸入「寫文案 {question}」。"

    def generate(
        self,
        topic: str = "",
        category_id: str = "policy_pitfall",
        platform: str = "facebook",
        tone: str = "專業權威且具親和力",
        property_data: Optional[Dict[str, Any]] = None,
        custom_hook: str = "",
        api_key_override: Optional[str] = None,
        provider_override: Optional[str] = None,
        enable_live_search: bool = True
    ) -> Dict[str, Any]:
        """
        生成爆款房產文章 (支援即時聯網比對與零幻覺防護)
        """
        # 1. 準備 Hook (若有明確主題，由 AI 針對該主題原創開頭金句，避免亂套不相關的貸款鉤子)
        if custom_hook:
            selected_hook = custom_hook
        elif topic and topic.strip():
            clean_t = topic.strip()
            selected_hook = f"請務必 100% 緊扣主題【{clean_t}】，為 Threads 量身原創第一句最吸睛、撕破痛點的爆款開頭金句 Hook。"
        else:
            selected_hook = "請根據台灣最新房市現況與自住客核心痛點，為 Threads 量身原創第一句最吸睛、撕破痛點的爆款開頭金句 Hook。"

        # 2. 即時聯網搜尋比對最新政策資訊
        live_data = {"has_live_data": False, "sources": [], "context_text": ""}
        if enable_live_search:
            region_hint = property_data.get("region", "") if property_data else ""
            search_query = topic if topic else (f"{region_hint} 房產政策 房貸" if region_hint else "台灣 房市政策 房貸")
            live_data = self.live_fetcher.build_live_grounding_context(search_query)

        # 3. 準備 Grounding 法規與知識庫背景 (結合本地核心法規庫 + 聯網即時資訊)
        static_grounding = self.validator.get_grounding_context(topic)
        combined_grounding = f"{static_grounding}\n\n{live_data.get('context_text', '')}"

        # 4. 判斷 AI 提供商與 Key（零伺服器環境變數殘留，一律由用戶端傳入）
        provider = provider_override or "gemini"
        gemini_key = api_key_override if provider == "gemini" else None
        openai_key = api_key_override if provider == "openai" else None

        # 5. 純 AI 生成（嚴格要求 AI 介入，無 Key 或呼叫失敗直接報錯反饋）
        generated_content = ""
        used_model = ""

        if provider == "gemini":
            if not gemini_key:
                return {
                    "success": False,
                    "error": "❌ 尚未輸入 Google Gemini API Key！本系統採零儲存隱私架構，請點擊右上角「⚙️ 模型與 API 設定」填入您個人的 Key 後再生成。",
                    "method": "gemini_api",
                    "content": "",
                    "validation": None,
                    "live_sources": live_data.get("sources", []),
                    "has_live_data": live_data.get("has_live_data", False)
                }
            try:
                generated_content, used_model = self._call_gemini(
                    api_key=gemini_key,
                    topic=topic,
                    category_id=category_id,
                    platform=platform,
                    tone=tone,
                    property_data=property_data,
                    hook=selected_hook,
                    grounding_context=combined_grounding
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"❌ Google Gemini AI 生成失敗：{str(e)}",
                    "method": "gemini_api",
                    "content": "",
                    "validation": None,
                    "live_sources": live_data.get("sources", []),
                    "has_live_data": live_data.get("has_live_data", False)
                }

        elif provider == "openai":
            if not openai_key:
                return {
                    "success": False,
                    "error": "❌ 尚未設定 OpenAI API Key！請點擊右上角「⚙️ 模型與 API 設定」填入 Key 後再進行生成。",
                    "method": "openai_api",
                    "content": "",
                    "validation": None,
                    "live_sources": live_data.get("sources", []),
                    "has_live_data": live_data.get("has_live_data", False)
                }
            try:
                generated_content, used_model = self._call_openai(
                    api_key=openai_key,
                    topic=topic,
                    category_id=category_id,
                    platform=platform,
                    tone=tone,
                    property_data=property_data,
                    hook=selected_hook,
                    grounding_context=combined_grounding
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"❌ OpenAI 生成失敗：{str(e)}",
                    "method": "openai_api",
                    "content": "",
                    "validation": None,
                    "live_sources": live_data.get("sources", []),
                    "has_live_data": live_data.get("has_live_data", False)
                }
        else:
            return {
                "success": False,
                "error": f"❌ 不支援的模型提供商：{provider}。請選擇 Google Gemini 或 OpenAI。",
                "method": "unknown",
                "content": "",
                "validation": None,
                "live_sources": live_data.get("sources", []),
                "has_live_data": live_data.get("has_live_data", False)
            }

        # 6. 反幻覺與法規事實檢核
        validation_result = self.validator.validate_content(generated_content)

        return {
            "success": True,
            "hook": selected_hook,
            "platform": platform,
            "category_id": category_id,
            "tone": tone,
            "method": f"{provider}_api",
            "used_model": used_model,
            "content": generated_content,
            "validation": validation_result,
            "live_sources": live_data.get("sources", []),
            "has_live_data": live_data.get("has_live_data", False)
        }

    def test_llm_connection(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        測試 AI 模型 API Key 與連線狀態
        """
        if not api_key:
            return {"success": False, "error": "請先輸入 API Key"}

        import requests
        if provider == "gemini":
            models_to_try = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            for m in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
                try:
                    res = requests.post(url, json=payload, timeout=10)
                    if res.status_code == 200:
                        return {"success": True, "provider": "gemini", "model": m, "message": f"Gemini ({m}) 連線成功！"}
                    elif res.status_code == 400:
                        return {"success": False, "error": f"API Key 無效或未開通 (HTTP 400): {res.text}"}
                except Exception as e:
                    pass
            return {"success": False, "error": "無法連線至 Google Gemini 伺服器，請檢查 API Key 是否正確。"}

        elif provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return {"success": True, "provider": "openai", "model": "gpt-4o-mini", "message": "OpenAI (GPT-4o-mini) 連線成功！"}
                else:
                    return {"success": False, "error": f"OpenAI 驗證失敗 (HTTP {res.status_code}): {res.text}"}
            except Exception as e:
                return {"success": False, "error": f"連線 OpenAI 異常: {str(e)}"}

        return {"success": True, "provider": "local", "message": "內建繁體中文動態範本引擎就緒"}

    def _call_gemini(
        self,
        api_key: str,
        topic: str,
        category_id: str,
        platform: str,
        tone: str,
        property_data: Optional[Dict[str, Any]],
        hook: str,
        grounding_context: str
    ) -> Tuple[str, str]:
        import requests
        prompt = self._build_llm_prompt(topic, category_id, platform, tone, property_data, hook, grounding_context)
        
        # 依序嘗試最新官方發布之 Gemini 模型 ID
        models_to_try = [
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro"
        ]
        last_err = ""
        
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 8192,
                    "thinkingConfig": {"thinkingBudget": 0}
                }
            }
            try:
                res = requests.post(url, json=payload, timeout=35)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            full_text = "".join([p.get("text", "") for p in parts if "text" in p and not p.get("thought", False)]).strip()
                            if full_text:
                                return full_text, m
                else:
                    last_err = f"Model {m} HTTP {res.status_code}: {res.text}"
            except Exception as e:
                last_err = str(e)
                
        raise RuntimeError(f"所有 Gemini 模型端點呼叫失敗: {last_err}")

    def _call_openai(
        self,
        api_key: str,
        topic: str,
        category_id: str,
        platform: str,
        tone: str,
        property_data: Optional[Dict[str, Any]],
        hook: str,
        grounding_context: str
    ) -> Tuple[str, str]:
        import requests
        prompt = self._build_llm_prompt(topic, category_id, platform, tone, property_data, hook, grounding_context)
        
        # 依序嘗試現代 OpenAI 模型
        models_to_try = ["gpt-4o-mini", "gpt-4o", "o3-mini", "gpt-3.5-turbo"]
        last_err = ""
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        for m in models_to_try:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": "你是一位頂級台灣房地產社群行銷操盤手兼房產法律顧問。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip(), m
                else:
                    last_err = f"Model {m} HTTP {res.status_code}: {res.text}"
            except Exception as e:
                last_err = str(e)
                
        raise RuntimeError(f"所有 OpenAI 模型呼叫失敗: {last_err}")

    def _build_llm_prompt(
        self,
        topic: str,
        category_id: str,
        platform: str,
        tone: str,
        property_data: Optional[Dict[str, Any]],
        hook: str,
        grounding_context: str
    ) -> str:
        has_prop = bool(property_data and any(str(v).strip() for v in property_data.values() if v))
        if has_prop:
            prop_str = f"""
【結構化物件行銷資訊（請自然融入文案）】：
- 物件案名/社區：{property_data.get('title') or '未指定'}
- 區域位置：{property_data.get('region') or ''}
- 格局與坪數：{property_data.get('layout') or ''} / {property_data.get('area') or ''} 坪
- 開價/總價區間：{property_data.get('price') or ''}
- 核心賣點/優勢：{property_data.get('highlights') or ''}
- 目標受眾：{property_data.get('target_buyer') or ''}
- 急迫感/特殊狀況：{property_data.get('urgency') or ''}
"""
        else:
            prop_str = """
【重要指示】：本篇為【純房市政策/時事議題分析文章】。
嚴格禁止捏造、杜撰或附加任何特定建案、社區、格局坪數或虛擬物件推薦（嚴禁出現「精選好房」、「合理行情價」、「📍精選標的」等字眼）！
全文請 100% 專注於政策分析、痛點剖析、數據事實與給自住客的實戰避坑建議。
"""

        platform_specs = {
            "facebook": "【Facebook 深度長文規格】：吸引人停下滑動的強大開頭 Hook、短段落（每段 1~2 句）、情緒引導（痛點-剖析-解法）、吸睛條列點、結尾具體 CTA（留言領取、私訊討論）。",
            "threads": "【Threads 爆款規格】：極致犀利直白、前兩行直接扎心撕破痛點、節奏明快（短行換行）、大白話撕開房市遮羞布、條列血淋淋數據真相、絕無公關空話、結尾留下爭議反問引爆留言區瘋狂討論（篇幅約 250~400 字）。",
            "instagram": "【Instagram 爆款圖文規格】：前言吸睛、卡片式重點拆解（Slide 1~5 視覺重點）、條列式乾貨、手機閱讀適配 Emoji、結尾互動與熱門 Hashtags。",
            "reels": "【Reels / 短影音黃金腳本規格】：0~3 秒視覺與開頭痛點鉤子、分鏡口播台詞對照表（痛點撕扯 -> 內幕反轉 -> 避坑解方 -> 行動召喚）、字幕提示與拍攝要點（適合 30~60 秒完播）。",
            "line": "【LINE 推播快訊規格】：簡潔有力的重點整理、適度加入 Emoji、標籤分類清晰、清楚的點擊諮詢或私訊引導。"
        }.get(platform, "適合社群傳播之格式")

        prompt = f"""
你現在是台灣頂尖的房地產自媒體爆款操盤手兼房市智囊。
請根據以下要求撰寫一篇極具傳播力、高點閱、高轉化，且「絕無法規與事實幻覺」的房產社群貼文。

【發布平台】：{platform}
{platform_specs}

【主題/核心訴求】：{topic or '台灣房市最新買房策略與關鍵避坑指南'}
【發文語氣】：{tone}
【指定開頭鉤子 (Hook)】：{hook}
{prop_str}

------------------------
【台灣最新房產法規與官方公告基準（嚴格遵守，禁止幻覺與猜測）】：
{grounding_context}
------------------------

【嚴格遵守的寫作與事實驗證要求】：
1. 開頭第一行必須直接使用指定的 Hook 或以此為基礎做最強力的發揮，嚴禁冗長的前言寒暄。
2. 涉及法規、貸款成數、寬限期、稅率時，一律嚴格遵循上述知識庫最新現行規定（例如央行第七波管制第二戶限貸5成無寬限期、新青安一生一次嚴查人頭等）。
3. 若提及「虛坪改革」等預告方案，必須明確註明為「政府預告/研議修法草案」，絕不可宣稱已強制實施。
4. 排版必須具備呼吸感，善用空行與重點標示符號，讓讀者在手機螢幕上 3 秒內被吸住。
5. 結尾請給出 1 個明確、低摩擦力的 Call to Action (行動呼籲)。
"""
        return prompt
