import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from typing import List, Dict, Any

class RealTimePolicyFetcher:
    """
    即時聯網房產資訊與法規比對檢索模組
    透過 Google News 台灣即時房產新聞 RSS 與政府公開來源，即時抓取最新政策、預告草案與市場動態
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def search_live_real_estate_news(self, query: str = "", max_results: int = 5) -> List[Dict[str, Any]]:
        """
        即時檢索台灣最新房市政策、法規與預告草案新聞
        """
        # 建構精準搜尋關鍵字
        search_terms = f"{query} 台灣 房產 OR 房貸 OR 信用管制 OR 內政部 OR 財政部 OR 央行" if query else "台灣 房市政策 房貸 央行 內政部 預告"
        encoded_query = urllib.parse.quote(search_terms)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

        articles = []
        try:
            req = urllib.request.Request(rss_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)

                for item in root.findall("./channel/item")[:max_results]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""

                    # 清理 HTML 標籤
                    clean_desc = re.sub(r"<[^>]+>", "", description).strip()

                    # 提取來源媒體
                    source = "即時新聞"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        title = parts[0]
                        source = parts[1]

                    articles.append({
                        "title": title,
                        "source": source,
                        "link": link,
                        "published_at": pub_date,
                        "summary": clean_desc
                    })
        except Exception as e:
            print(f"[RealTimePolicyFetcher] 即時聯網檢索異常: {e}")

        return articles

    def build_live_grounding_context(self, topic: str = "") -> Dict[str, Any]:
        """
        產生即時聯網比對上下文，供 AI 生成與反幻覺檢核使用
        """
        live_articles = self.search_live_real_estate_news(topic, max_results=4)
        
        if not live_articles:
            return {
                "has_live_data": False,
                "sources": [],
                "context_text": "【即時聯網檢索】：未取得即時新聞，依據現有最新官方知識庫基準。"
            }

        lines = ["【🌐 網路上最新即時房市政策與動態資訊（即時聯網比對）】："]
        for idx, art in enumerate(live_articles, 1):
            lines.append(f"{idx}. 《{art['title']}》（來源：{art['source']} | 時間：{art['published_at']}）")
            if art['summary']:
                lines.append(f"   摘要：{art['summary']}")
        
        return {
            "has_live_data": True,
            "sources": live_articles,
            "context_text": "\n".join(lines)
        }
