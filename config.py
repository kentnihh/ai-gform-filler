import os
import yaml
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the application environment variables.
    
    Attributes:
        MODEL (str): The name of the model to use (e.g., 'qwen2.5:0.5b').
        MIN_DELAY (float): Minimum delay in seconds for human-like interactions.
        MAX_DELAY (float): Maximum delay in seconds for human-like interactions.
        MAX_RETRIES (int): Maximum number of retry attempts for API calls or DOM actions.
        HEADLESS (bool): Whether to run the Playwright browser in headless mode.
        PROXY_URL (str): Optional proxy server URL for Playwright.
    """
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL: str = os.getenv("MODEL", "llama3.2")
    MIN_DELAY: float = float(os.getenv("MIN_DELAY", "3.0"))
    MAX_DELAY: float = float(os.getenv("MAX_DELAY", "8.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    HEADLESS: bool = True  # Strictly enforced to save RAM/GPU
    PROXY_URL: str = os.getenv("PROXY_URL", "")
    
    # Demographics loaded from config.yaml
    DEMOGRAPHICS: dict = {}

    @classmethod
    def validate(cls) -> None:
        """Validates the configuration parameters.
        
        Currently acts as a placeholder since local Ollama does not require an API key.
        """
        pass

    @classmethod
    def load_yaml(cls, path: str = "config.yaml") -> None:
        """Loads demographic distributions from config.yaml"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cls.DEMOGRAPHICS = data.get("demographics", {})
        else:
            cls.DEMOGRAPHICS = {
                "genders": ["Laki-laki", "Perempuan"],
                "frequencies": ["Pertama Kali", "Jarang", "Kadang-kadang", "Sering", "Sangat Sering"],
                "attitudes": ["Sangat Puas & Kritis", "Netral", "Cenderung Positif", "Cepat Puas", "Kritis & Detail"]
            }

# Initialize yaml load on import
Config.load_yaml()