import json
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from core.engine import ViralPostEngine
from core.validator import PolicyValidator
from core.line_bot import LineBotHandler
from core.policy_updater import AutomatedPolicyUpdater

app = FastAPI(
    title="房地產爆款發文模型系統",
    description="專為台灣房地產設計的爆款文案生成、法規反幻覺校驗與 LINE Bot 整合系統",
    version="1.0.0"
)

def ensure_knowledge_files():
    """即使在 Zeabur 掛載空白 Volume 時，也自動從 default_knowledge 還原基礎法規與鉤子庫"""
    import shutil
    k_dir = settings.KNOWLEDGE_DIR
    def_dir = settings.BASE_DIR / "default_knowledge"
    k_dir.mkdir(parents=True, exist_ok=True)
    if def_dir.exists():
        for fname in ["taiwan_policies.json", "viral_hooks.json", "real_estate_terms.json"]:
            target = k_dir / fname
            src = def_dir / fname
            if src.exists() and (not target.exists() or target.stat().st_size == 0):
                try:
                    shutil.copy2(src, target)
                    print(f"[Knowledge] 已自動修復並初始化知識庫: {fname}", flush=True)
                except Exception as e:
                    print(f"[Knowledge] 初始化失敗: {e}", flush=True)

ensure_knowledge_files()

# 初始化核心引擎與模組
engine = ViralPostEngine(settings.KNOWLEDGE_DIR)
validator = PolicyValidator(settings.KNOWLEDGE_DIR)
line_handler = LineBotHandler(engine)
policy_updater = AutomatedPolicyUpdater(settings.KNOWLEDGE_DIR, settings.DATA_DIR)

# 掛載靜態資源目錄
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 請求 Model 定義
class PropertyData(BaseModel):
    title: Optional[str] = ""
    region: Optional[str] = ""
    price: Optional[str] = ""
    area: Optional[str] = ""
    layout: Optional[str] = ""
    highlights: Optional[str] = ""
    target_buyer: Optional[str] = ""
    urgency: Optional[str] = ""

class GenerateRequest(BaseModel):
    topic: Optional[str] = ""
    category_id: Optional[str] = "policy_pitfall"
    platform: Optional[str] = "facebook"
    tone: Optional[str] = "專業權威且具親和力"
    property_data: Optional[PropertyData] = None
    custom_hook: Optional[str] = ""
    api_key: Optional[str] = ""
    provider: Optional[str] = ""
    enable_live_search: Optional[bool] = True

class ValidateRequest(BaseModel):
    content: str

class LineSimulateRequest(BaseModel):
    message: str
    user_id: Optional[str] = "mock_user_001"
    api_key: Optional[str] = ""

class TestConnectionRequest(BaseModel):
    provider: str
    api_key: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>房地產爆款發文模型系統啟動成功</h1><p>請確認 static/index.html 是否存在</p>")

@app.post("/")
async def serve_root_post(request: Request, x_line_signature: Optional[str] = Header(None)):
    """若 LINE 後台誤將 Webhook 填為根目錄網址，自動轉交 line_webhook 處理"""
    return await line_webhook(request, x_line_signature)

@app.post("/api/test-connection")
async def test_connection(req: TestConnectionRequest):
    """測試 API Key 與提供商連線狀態"""
    result = engine.test_llm_connection(req.provider, req.api_key)
    return result

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "policies_loaded": len(validator.policies),
        "hook_categories": len(engine.get_hook_categories()),
        "llm_provider": settings.LINE_BOT_AI_PROVIDER,
        "line_configured": bool(settings.LINE_CHANNEL_SECRET and settings.LINE_CHANNEL_ACCESS_TOKEN)
    }

@app.get("/api/policies")
async def get_policies():
    """獲取台灣最新房產法規與預告草案知識庫"""
    return {
        "policies": validator.policies,
        "terms": validator.terms
    }

class SyncLivePoliciesRequest(BaseModel):
    api_key: Optional[str] = ""
    provider: Optional[str] = ""
    custom_keyword: Optional[str] = ""

@app.post("/api/policies/sync-live")
async def sync_live_policies(req: Optional[SyncLivePoliciesRequest] = None):
    """即時連網爬取台灣最新房市政策、草案與新聞，並自動更新寫入 taiwan_policies.json"""
    api_key = req.api_key if req else ""
    provider = req.provider if req else ""
    custom_keyword = req.custom_keyword if req else ""
    sync_result = policy_updater.sync_and_update_knowledge(
        api_key=api_key, provider=provider, custom_keyword=custom_keyword
    )
    
    # 熱重載驗證器內的法規與術語清單
    validator.policies = validator._load_policies()
    validator.terms = validator._load_terms()
    
    return {
        "success": True,
        "sync_result": sync_result,
        "policies": validator.policies,
        "terms": validator.terms
    }

@app.get("/api/hooks")
async def get_hooks(category_id: Optional[str] = None):
    """獲取爆款鉤子庫清單"""
    categories = engine.get_hook_categories()
    if category_id:
        categories = [c for c in categories if c.get("id") == category_id]
    return {"categories": categories}

class GenerateHooksRequest(BaseModel):
    topic: Optional[str] = ""
    category_id: Optional[str] = "policy_pitfall"
    property_data: Optional[PropertyData] = None
    api_key: Optional[str] = ""
    provider: Optional[str] = ""

@app.post("/api/hooks/generate")
async def generate_custom_hooks(req: GenerateHooksRequest):
    """AI 針對特定主題即時客製化產出 5 組專屬爆款鉤子"""
    prop_dict = None
    if req.property_data:
        raw_dict = req.property_data.dict()
        if any(str(v).strip() for v in raw_dict.values() if v):
            prop_dict = raw_dict
    hooks = engine.generate_dynamic_hooks(
        topic=req.topic or "",
        category_id=req.category_id or "policy_pitfall",
        property_data=prop_dict,
        api_key_override=req.api_key if req.api_key else None,
        provider_override=req.provider if req.provider else None
    )
    return {"hooks": hooks}

@app.post("/api/generate")
async def generate_post(req: GenerateRequest):
    """生成爆款房產社群文案與事實檢核 (自動聯網檢索比對)"""
    prop_dict = None
    if req.property_data:
        raw_dict = req.property_data.dict()
        if any(str(v).strip() for v in raw_dict.values() if v):
            prop_dict = raw_dict

    print(f"\n📥 [收到產文請求條件]:")
    print(f"  • 主題 (Topic): '{req.topic}'")
    print(f"  • 切角分類 (Category): '{req.category_id}'")
    print(f"  • 目標平台 (Platform): '{req.platform}'")
    print(f"  • 發文語氣 (Tone): '{req.tone}'")
    print(f"  • 指定鉤子 (Custom Hook): '{req.custom_hook}'")
    print(f"  • 物件資料 (Property Data): {prop_dict}")
    print(f"  • 即時聯網開關 (Live Search): {req.enable_live_search}")
    print(f"  • 提供商 (Provider): '{req.provider}' (Key長度: {len(req.api_key or '')})")

    result = engine.generate(
        topic=req.topic or "",
        category_id=req.category_id or "policy_pitfall",
        platform=req.platform or "facebook",
        tone=req.tone or "專業權威且具親和力",
        property_data=prop_dict,
        custom_hook=req.custom_hook or "",
        api_key_override=req.api_key if req.api_key else None,
        provider_override=req.provider if req.provider else None,
        enable_live_search=req.enable_live_search if req.enable_live_search is not None else True
    )
    return result

@app.post("/api/validate")
async def validate_custom_post(req: ValidateRequest):
    """手動檢核文案的房產法規正確性與反幻覺報告"""
    result = validator.validate_content(req.content)
    return result

@app.post("/api/line/simulate")
async def simulate_line_message(req: LineSimulateRequest):
    """在 Web 控制台模擬 LINE Bot 對話測試（支援用戶配額模擬）"""
    reply = line_handler.handle_message_text(
        text=req.message,
        user_id=req.user_id or "mock_user_001",
        api_key_override=req.api_key or None
    )
    return {"reply": reply}

import sys
from datetime import datetime

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method
    
    # 針對 Webhook 與 API 請求進行即時標記
    if path in ["/callback", "/callback/", "/"] and method == "POST":
        print(f"\n🔔 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收到外部 Webhook POST 請求：路徑={path} | 來源IP={client_ip}", flush=True)

    response = await call_next(request)
    return response

@app.api_route("/callback", methods=["GET", "POST", "HEAD"])
@app.api_route("/callback/", methods=["GET", "POST", "HEAD"])
async def line_webhook(request: Request, x_line_signature: Optional[str] = Header(None)):
    """LINE Messaging API 官方 Webhook 入口 (支援 Verify 探測與真實事件)"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 針對 GET / HEAD 探測請求直接回傳 200 OK
    if request.method in ["GET", "HEAD"]:
        print(f"[{now_str}] 收到 GET/HEAD 探測請求，回傳 200 OK", flush=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "message": "LINE Webhook endpoint is healthy."})

    body = await request.body()
    body_str = body.decode("utf-8")

    print(f"\n==================== [LINE Webhook 事件進入] ====================", flush=True)
    print(f"• 時間: {now_str}", flush=True)
    print(f"• X-Line-Signature: '{x_line_signature or ''}'", flush=True)
    print(f"• Body 長度: {len(body_str)} 字元", flush=True)
    print(f"• Body 內容: {body_str[:300]}", flush=True)
    print(f"• 伺服器 Secret 配置狀態: {'已填寫 (長度: ' + str(len(settings.LINE_CHANNEL_SECRET)) + ')' if settings.LINE_CHANNEL_SECRET else '❌ 尚未填寫'}", flush=True)
    print(f"• 伺服器 Token 配置狀態: {'已填寫 (長度: ' + str(len(settings.LINE_CHANNEL_ACCESS_TOKEN)) + ')' if settings.LINE_CHANNEL_ACCESS_TOKEN else '❌ 尚未填寫'}", flush=True)

    # LINE Verify 探測時通常發送空 body 或空 events 陣列
    if not body_str or body_str.strip() == "{}":
        print("• 判定為空探測請求，直接回傳 200 OK", flush=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})

    # 若尚未在伺服器設定 LINE 憑證
    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        print("⚠️ 伺服器尚未設定 LINE_CHANNEL_SECRET 或 LINE_CHANNEL_ACCESS_TOKEN，請於 Zeabur Variables 填入。", flush=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "message": "Webhook received. Credentials not configured yet."}
        )

    try:
        from linebot.v3 import WebhookParser
        from linebot.v3.messaging import (
            Configuration,
            ApiClient,
            MessagingApi,
            ReplyMessageRequest,
            TextMessage,
            ShowLoadingAnimationRequest
        )
        from linebot.v3.webhooks import MessageEvent, TextMessageContent

        parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
        events = parser.parse(body_str, x_line_signature or "")
        
        print(f"• 成功解析事件數: {len(events)} 個", flush=True)
        if not events:
            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})

        configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            for idx, event in enumerate(events, 1):
                if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                    user_msg = event.message.text
                    user_id = event.source.user_id if hasattr(event.source, "user_id") else "line_real_user"
                    print(f"  [{idx}] 處理用戶訊息 | UserID: {user_id} | 內容: '{user_msg}'", flush=True)
                    
                    # 1. 立即觸發手機端 LINE 讀取中動畫（「...」動畫，提升使用者體驗）
                    try:
                        line_bot_api.show_loading_animation(
                            ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=30)
                        )
                        print(f"  [{idx}] ⏳ 已觸發手機端 LINE 讀取中動畫...", flush=True)
                    except Exception as load_err:
                        print(f"  [{idx}] 觸發讀取動畫通知 (非致命): {load_err}", flush=True)

                    # 2. 進行 AI 原創生成與法規檢核
                    reply_text = line_handler.handle_message_text(user_msg, user_id=user_id)
                    print(f"  [{idx}] 產出回覆內容 (長度: {len(reply_text)})，正在呼叫 LINE API 送出...", flush=True)
                    
                    # LINE 官方限制單一文字訊息最多 5000 字元
                    safe_reply_text = reply_text if len(reply_text) <= 4900 else reply_text[:4900] + "\n\n...(篇幅過長已自動截斷)"
                    
                    try:
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=[TextMessage(text=safe_reply_text)]
                            )
                        )
                        print(f"  [{idx}] ✅ LINE 訊息成功送達用戶手機！", flush=True)
                    except Exception as api_err:
                        print(f"  [{idx}] ❌ 呼叫 LINE Messaging API 送出回覆失敗: {api_err}", flush=True)
                        if hasattr(api_err, "body"):
                            print(f"  [{idx}] LINE 官方回傳錯誤詳情: {api_err.body}", flush=True)
                    
        print(f"=================================================================\n", flush=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
    except Exception as e:
        import traceback
        print(f"❌ LINE Webhook 處理異常: {e}\n{traceback.format_exc()}", flush=True)
        print(f"=================================================================\n", flush=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "handled_with_warning", "detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
