import pytest
from pathlib import Path
from core.validator import PolicyValidator
from core.engine import ViralPostEngine
from core.line_bot import LineBotHandler
from core.quota_manager import QuotaManager
from core.policy_updater import AutomatedPolicyUpdater

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DATA_DIR = BASE_DIR / "data"

def test_knowledge_files_exist_and_valid():
    """驗證法規、術語與鉤子知識庫完整且不為空"""
    assert (KNOWLEDGE_DIR / "taiwan_policies.json").exists()
    assert (KNOWLEDGE_DIR / "viral_hooks.json").exists()
    assert (KNOWLEDGE_DIR / "real_estate_terms.json").exists()

    validator = PolicyValidator(KNOWLEDGE_DIR)
    assert len(validator.policies) >= 5
    assert len(validator.terms) >= 5

def test_validator_detects_hallucinations():
    """驗證反幻覺引擎能精確攔截不實、炒作或已失效法規"""
    validator = PolicyValidator(KNOWLEDGE_DIR)
    
    # 測試 1: 錯誤貸款成數 (第二戶宣稱可貸8成)
    bad_text = "央行最新政策下，第二戶房貸最高可貸8成，還有3年寬限期喔！"
    result = validator.validate_content(bad_text)
    assert not result["is_valid"]
    assert any("第二戶" in w for w in result["warnings"])
    
    # 測試 2: 新青安違規轉租
    illegal_text = "教你用新青安買來出租當包租公，爽賺租金！"
    result2 = validator.validate_content(illegal_text)
    assert not result2["is_valid"]
    assert any("嚴禁出租" in w for w in result2["warnings"])

    # 測試 3: 預售屋轉約炒作
    illegal_flip = "這間預售屋買完可以隨時換約轉讓賺差價！"
    result3 = validator.validate_content(illegal_flip)
    assert not result3["is_valid"]
    assert any("平均地權條例" in w for w in result3["warnings"])

def test_validator_passes_compliant_text():
    """驗證符合最新法規與草案標示的文案能順利通過"""
    validator = PolicyValidator(KNOWLEDGE_DIR)
    good_text = """
    在央行第七波信用管制下，第二戶最高只能貸5成且無寬限期。
    新青安貸款一生一次自住上限1000萬，新婚加碼至1200萬。
    另外內政部預告中的虛坪改革草案目前推動中。
    """
    result = validator.validate_content(good_text)
    assert result["is_valid"]
    assert len(result["warnings"]) == 0
    assert len(result["passed_checks"]) >= 2

def test_engine_pure_ai_failure_without_key():
    """驗證純 AI 模式下，未輸入 API Key 時嚴格拒絕生成並返回明確錯誤"""
    engine = ViralPostEngine(KNOWLEDGE_DIR)
    
    res = engine.generate(topic="換屋自救攻略", platform="facebook")
    assert not res["success"]
    assert "尚未輸入" in res["error"]
    assert res["content"] == ""

def test_engine_generation_with_mock_llm(monkeypatch):
    """驗證提供有效 LLM 輸出時，格式、法規檢核與來源標籤完整返回"""
    engine = ViralPostEngine(KNOWLEDGE_DIR)
    
    mock_ai_output = """新婚夫妻看過來！新青安 3.0 額度加碼到 1200 萬，但總價超過這數字一毛都貸不到...

在央行第七波信用管制下，第二戶最高只能貸5成且無寬限期。
新青安貸款一生一次自住上限1000萬，新婚加碼至1200萬。
另外內政部預告中的虛坪改革草案目前推動中。
"""
    monkeypatch.setattr(engine, "_call_gemini", lambda **kwargs: (mock_ai_output, "gemini-2.5-flash"))
    
    res = engine.generate(
        topic="新青安 3.0",
        platform="facebook",
        api_key_override="test_valid_key",
        provider_override="gemini"
    )
    
    assert res["success"]
    assert res["used_model"] == "gemini-2.5-flash"
    assert "新青安" in res["content"]
    assert res["validation"]["is_valid"]

def test_anti_fake_placeholder_in_pure_topic():
    """驗證純議題模式絕不輸出假物件佔位符"""
    engine = ViralPostEngine(KNOWLEDGE_DIR)
    prompt = engine._build_llm_prompt(
        topic="囤房稅 2.0 稅率剖析",
        category_id="policy_pitfall",
        platform="facebook",
        tone="專業",
        property_data=None,
        hook="開頭第一句",
        grounding_context="法規背景"
    )
    assert "純房市政策/時事議題分析文章" in prompt
    assert "嚴格禁止捏造" in prompt
    assert "精選好房" in prompt # 指令中明確提及嚴禁精選好房

import uuid

def test_quota_manager_complete_lifecycle():
    """驗證配額管理引擎完整生命週期：3次耗盡扣除、超額攔截、VIP 兌換解鎖"""
    qm = QuotaManager(DATA_DIR)
    uid = f"test_lifecycle_{uuid.uuid4().hex[:8]}"

    # 1. 初始 3 次
    status = qm.get_user_status(uid)
    assert status["role"] == "免費會員"
    assert "3 次" in status["remaining_quota"]

    # 2. 消耗第 1 次
    r1 = qm.check_and_consume_quota(uid)
    assert r1["allowed"]
    assert r1["remaining"] == 2

    # 3. 消耗第 2 次
    r2 = qm.check_and_consume_quota(uid)
    assert r2["allowed"]
    assert r2["remaining"] == 1

    # 4. 消耗第 3 次
    r3 = qm.check_and_consume_quota(uid)
    assert r3["allowed"]
    assert r3["remaining"] == 0

    # 5. 第 4 次嘗試消耗 -> 嚴格攔截
    r4 = qm.check_and_consume_quota(uid)
    assert not r4["allowed"]
    assert "已用完" in r4["message"]

    # 6. 兌換 VIP
    redeem_res = qm.redeem_code(uid, "VIP888")
    assert redeem_res["success"]
    assert redeem_res["role"] == "vip"

    # 7. VIP 消耗 -> 無限次通行
    r5 = qm.check_and_consume_quota(uid)
    assert r5["allowed"]
    assert r5["role"] == "vip"

def test_line_bot_commands_and_quota_integration():
    """驗證 LINE Bot 整合測試"""
    engine = ViralPostEngine(KNOWLEDGE_DIR)
    handler = LineBotHandler(engine)
    test_uid = f"line_integration_{uuid.uuid4().hex[:8]}"
    
    # 測試 help
    help_reply = handler.handle_message_text("help", user_id=test_uid)
    assert "房地產爆款發文機器人" in help_reply
    
    # 測試 額度查詢
    quota_reply = handler.handle_message_text("額度", user_id=test_uid)
    assert "今日剩餘額度" in quota_reply
    
    # 測試 兌換碼啟動 VIP
    redeem_reply = handler.handle_message_text("兌換 VIP888", user_id=test_uid)
    assert "恭喜" in redeem_reply
    assert "VIP" in redeem_reply
    
    # 測試 日常打招呼（免扣額度且親切引導）
    greet_reply = handler.handle_message_text("你好阿", user_id=test_uid)
    assert "您好！我是房地產爆款發文助手" in greet_reply
    assert "想產出什麼房市主題" in greet_reply

def test_line_webhook_verify_endpoint():
    """驗證 LINE Webhook Verify 探測請求與 GET/POST/HEAD 路由狀態一律回傳 200"""
    from fastapi.testclient import TestClient
    from app import app
    
    client = TestClient(app)
    
    # 1. 測試 GET /callback
    r_get = client.get("/callback")
    assert r_get.status_code == 200
    
    # 2. 測試 POST /callback 空 body 探測
    r_post = client.post("/callback", json={})
    assert r_post.status_code == 200
    
    # 3. 測試結尾帶斜線 /callback/
    r_slash = client.post("/callback/", json={"events": []})
    assert r_slash.status_code == 200
