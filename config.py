import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL: str = os.getenv("MODEL", "gpt-4o-mini")
    MIN_DELAY: float = float(os.getenv("MIN_DELAY", "3.0"))
    MAX_DELAY: float = float(os.getenv("MAX_DELAY", "8.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY belum diset pada file .env")