import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # 服務配置
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # LINE Bot 專屬後端 AI 金鑰配置 (SaaS 託管與配額制專用，Web 控制台一律由用戶端傳入)
    LINE_BOT_AI_PROVIDER: str = os.getenv("LINE_BOT_AI_PROVIDER", "gemini")
    LINE_BOT_AI_API_KEY: str = os.getenv("LINE_BOT_AI_API_KEY", "")
    
    # LINE Messaging API 憑證
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    
    # 資料路徑
    KNOWLEDGE_DIR: Path = BASE_DIR / "knowledge"
    DATA_DIR: Path = BASE_DIR / "data"

settings = Settings()
