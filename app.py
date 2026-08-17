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

app = FastAPI(
    title="房地產爆款發文模型系統",
    description="專為台灣房地產設計的爆款文案生成、法規反幻覺校驗與 LINE Bot 整合系統",
    version="1.0.0"
)

from core.policy_updater import AutomatedPolicyUpdater

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
        "llm_provider": settings.DEFAULT_LLM_PROVIDER,
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

@app.post("/callback")
async def line_webhook(request: Request, x_line_signature: Optional[str] = Header(None)):
    """LINE Messaging API 官方 Webhook 入口"""
    body = await request.body()
    body_str = body.decode("utf-8")

    # 若未設定 LINE 憑證，回傳簡易確認
    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "LINE Webhook received, but credentials not configured yet."}
        )

    try:
        from linebot.v3 import WebhookParser
        from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
        from linebot.v3.webhooks import MessageEvent, TextMessageContent

        parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
        events = parser.parse(body_str, x_line_signature)
        
        configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        async with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            for event in events:
                if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                    user_msg = event.message.text
                    user_id = event.source.user_id if hasattr(event.source, "user_id") else "line_real_user"
                    reply_text = line_handler.handle_message_text(user_msg, user_id=user_id)
                    await line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_text)]
                        )
                    )
        return "OK"
    except Exception as e:
        print(f"LINE Webhook 處理失敗: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
