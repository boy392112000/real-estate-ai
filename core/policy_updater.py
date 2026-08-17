import json
import shutil
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import settings

class AutomatedPolicyUpdater:
    """
    台灣房產法規與預告草案自動爬取、AI 結構化解析與知識庫自動寫入引擎
    """
    def __init__(self, knowledge_dir: Path, data_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.data_dir = data_dir
        self.policies_path = self.knowledge_dir / "taiwan_policies.json"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_latest_official_signals(self, custom_keyword: Optional[str] = None) -> List[Dict[str, str]]:
        """
        全方位爬取台灣房地產六大領域官方發布與最新動態（或指定自訂主題）
        """
        # 全方位房地產領域矩陣
        if custom_keyword and custom_keyword.strip():
            queries = [
                f"{custom_keyword.strip()} 台灣 房產 法規",
                f"{custom_keyword.strip()} 內政部 財政部 央行 公告",
                f"{custom_keyword.strip()} 政策 草案 最新"
            ]
        else:
            queries = [
                # 1. 金融貸款與信用管制
                "中央銀行 選擇性信用管制 房貸成數 寬限期 銀行法72-2",
                "財政部 青年安心成家 購屋優惠貸款 新青安 額度 排富",
                # 2. 不動產稅制與持有成本
                "財政部 房屋稅 囤房稅2.0 全國歸戶 差別稅率",
                "財政部 房地合一稅 交易所得 自住優惠 稅率",
                # 3. 交易市場管制與消保防弊
                "內政部 平均地權條例 預售屋 換約轉售 炒房 罰鍰",
                "內政部 預售屋買賣定型化契約 履約保證 實價登錄 申報",
                # 4. 建築技術、虛坪與土地法規
                "內政部 虛坪改革方案 公設比 車位產權 免計容積 草案",
                "內政部 國土計畫法 功能分區 土地使用管制 轉軌",
                # 5. 都更危老與改建容積獎勵
                "內政部 都市更新條例 危老重建 容積獎勵 耐震評估",
                # 6. 租賃專法與社會住宅政策
                "內政部 租賃住宅市場發展條例 租金補貼 包租代管"
            ]

        collected_signals = []
        for q in queries:
            encoded_query = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                req = urllib.request.Request(rss_url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=8) as res:
                    root = ET.fromstring(res.read())
                    for item in root.findall("./channel/item")[:2]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        description = item.find("description").text if item.find("description") is not None else ""
                        clean_desc = re.sub(r"<[^>]+>", "", description).strip()
                        collected_signals.append({
                            "query": q,
                            "title": title,
                            "pub_date": pub_date,
                            "summary": clean_desc
                        })
            except Exception as e:
                pass

        return collected_signals

    def sync_and_update_knowledge(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        custom_keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        全領域爬取最新訊號 -> AI 智能比對與結構化更新 -> 寫入 taiwan_policies.json
        """
        signals = self.fetch_latest_official_signals(custom_keyword=custom_keyword)
        
        # 讀取現有法規
        current_data = {"policies": []}
        if self.policies_path.exists():
            with open(self.policies_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)

        provider_name = provider or "gemini"
        key = api_key

        updated_policies = []
        sync_method = "rule_based_sync"

        # 若有 AI Key 則進行 LLM 深度結構化更新，若無則依最新爬蟲訊號自動校驗時間戳
        if key:
            try:
                updated_policies = self._ai_extract_policies(signals, current_data.get("policies", []), key, provider_name)
                sync_method = f"{provider_name}_ai_auto_update"
            except Exception as e:
                print(f"[PolicyUpdater] AI 結構化更新失敗，使用現有基礎更新: {e}")
                updated_policies = current_data.get("policies", [])
        else:
            updated_policies = current_data.get("policies", [])

        # 備份既有檔案
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.policies_path.exists():
            backup_file = self.backup_dir / f"taiwan_policies_backup_{timestamp}.json"
            shutil.copy(self.policies_path, backup_file)

        # 寫入最新版政策知識庫
        new_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": f"2026.auto.{timestamp[:8]}",
            "sync_method": sync_method,
            "signals_analyzed_count": len(signals),
            "policies": updated_policies
        }

        with open(self.policies_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)

        # 讀取並更新術語庫時間戳與備份
        terms_path = self.knowledge_dir / "real_estate_terms.json"
        terms_count = 0
        if terms_path.exists():
            with open(terms_path, "r", encoding="utf-8") as f:
                terms_data = json.load(f)
            terms_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            terms_count = len(terms_data.get("terms", []))
            with open(terms_path, "w", encoding="utf-8") as f:
                json.dump(terms_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "last_updated": new_data["last_updated"],
            "version": new_data["version"],
            "sync_method": sync_method,
            "signals_count": len(signals),
            "policies_count": len(updated_policies),
            "terms_count": terms_count,
            "signals_sample": signals[:4]
        }

    def _ai_extract_policies(
        self,
        signals: List[Dict[str, str]],
        existing_policies: List[Dict[str, Any]],
        api_key: str,
        provider: str
    ) -> List[Dict[str, Any]]:
        """
        利用 LLM 將網路最新官方動態與草案訊號合併至既有政策庫
        """
        import requests

        signal_text = "\n".join([f"- {s['title']} ({s['pub_date']}): {s['summary']}" for s in signals])
        existing_text = json.dumps(existing_policies, ensure_ascii=False, indent=2)

        prompt = f"""
你是一位台灣不動產法規專家與資料庫架構師。
請根據下方【網路上最新抓取的政府公告與新聞訊號】，檢視並更新【現有台灣房產法規與草案資料庫】。

【最新官方與新聞訊號】：
{signal_text}

【現有法規資料庫內容】：
{existing_text}

【任務要求】：
1. 檢查是否有任何新政策、新規範（例如新青安 3.0 的 1500 萬加碼、年齡限制、排富、3+3補貼、央行信用管制修正、虛坪改革草案進度）。
2. 更新每一項法規的狀態（現行實施中 或 政策預告草案）、主管機關、關鍵規則與防幻覺底線。
3. 嚴格輸出合法的 JSON Array（僅輸出 JSON 陣列，不要有任何 Markdown 代碼框或額外文字），格式與現有 policies 陣列一致。
"""

        if provider == "gemini":
            models = ["gemini-3.7-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            clean_key = api_key.strip()
            for m in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={clean_key}"
                gen_cfg = {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 8192
                }
                if "3." in m or "2.0" in m:
                    gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": gen_cfg
                }
                res = requests.post(url, json=payload, timeout=35)
                if res.status_code == 200:
                    candidates = res.json().get("candidates", [])
                    if candidates:
                        raw_parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join([p.get("text", "") for p in raw_parts if "text" in p and not p.get("thought", False)]).strip()
                        if text:
                            return json.loads(text)

        elif provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                raw_json = json.loads(res.json()["choices"][0]["message"]["content"])
                return raw_json if isinstance(raw_json, list) else raw_json.get("policies", existing_policies)

        return existing_policies
