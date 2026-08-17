# 房地產爆款發文模型系統 (Real Estate Viral Content Engine)

專為台灣房地產市場量身打造的 **社群爆款發文生成、零幻覺最新法規校驗與 LINE 機器人** 系統。

---

## 🌟 核心特色

1. **零幻覺與最新政策知識庫 (Anti-Hallucination Policy Engine)**：
   - 內建台灣最新房產法規（**央行第七波信用管制**、**新青安精進加嚴規定**、**囤房稅 2.0 全國歸戶**、**平均地權條例禁止預售轉約**、**房地合一 2.0**）。
   - 納入政府研議預告之草案（**內政部虛坪改革方案**、**國土計畫法**），嚴格標註預告狀態，杜絕時空錯亂與虛假承諾。
   - 內建自動事實驗證層，對生成內容即時攔截不實或過期的貸款成數與條文。

2. **50+ 房產社群爆款鉤子庫 (Viral Hook Generator)**：
   - 五大切角：**政策解讀與買房避坑 (PAS)**、**真實故事與情感共鳴**、**物件行銷與精準轉化 (AIDA)**、**爭議話題與社群論戰**、**內幕踢爆與行家攻略**。

3. **四大多平台格式一鍵轉發**：
   - **Facebook**：社群長文、情境痛點、結構化排版、強 CTA。
   - **Threads**：短節奏、高衝擊開頭、痛點撕扯金句。
   - **Instagram**：5~7 張輪播圖文卡片腳本 (Slide 1~5) + Caption。
   - **LINE**：私域群組推播、案場快訊整理。

4. **全 Docker Compose 容器化隔離**：
   - 地端環境保持 100% 純淨，無需安裝額外 Python 環境。
   - 知識庫與產出資料夾（`knowledge/`、`data/`）持久化掛載，地端隨時修改 JSON 即刻熱生效。

5. **LINE Bot 機器人對話串接**：
   - 內建 FastAPI Webhook 路由（`/callback`）與自然語言指令處理器。
   - 支援在 LINE 聊天室直接輸入物件參數或房市主題產出爆款文案。

---

## 🚀 快速啟動 (Docker Compose)

### 1. 複製設定檔並填入 API Key（選填）
```bash
cp .env.example .env
```
> 若無 API Key，系統將自動啟用內建的高質感繁中爆款範本引擎，依然具備完整的法規防幻覺檢核與多平台排版功能！

### 2. 一鍵建置與啟動容器
```bash
docker compose up -d --build
```

### 3. 開啟 Web 創作控制台
瀏覽器直接開啟：
👉 **http://localhost:8000**

---

## 🧪 容器內自動化測試
可在 Docker 容器內執行完整單元與整合測試：
```bash
docker compose exec app pytest
```

---

## 📂 目錄結構
```text
房地產發文模型/
├── docker-compose.yml          # Docker Compose 容器編排
├── Dockerfile                  # Python 3.11 隔離環境映像
├── requirements.txt            # 相依套件
├── app.py                      # FastAPI 伺服器與 LINE Webhook
├── config.py                   # 設定模組
├── core/
│   ├── engine.py               # 爆款生成核心與多平台轉換
│   ├── validator.py            # 反幻覺與最新法規檢核模組
│   └── line_bot.py             # LINE Bot 訊息處理器
├── knowledge/                  # 地端可隨時擴充與編輯的知識庫
│   ├── taiwan_policies.json    # 現行法規 + 預告草案資料庫
│   ├── viral_hooks.json        # 50+ 房產爆款鉤子庫
│   └── real_estate_terms.json  # 台灣在地房產避坑術語庫
├── static/                     # Web 創作控制台
│   ├── index.html              # 現代雙欄控制台介面
│   ├── style.css               # 高級感原生 CSS
│   └── app.js                  # 前端互動與 LINE 模擬
└── tests/
    └── test_core.py            # 自動化檢核測試腳本
```
