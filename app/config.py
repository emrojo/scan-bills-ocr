import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "ScanBills OCR Service"
    version: str = "1.0.0"
    
    # Ollama Backend Settings
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    default_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
    fallback_model: str = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5vl:3b")
    
    # OCR & Preprocessing
    pdf_dpi: int = int(os.getenv("PDF_DPI", "200"))
    max_image_dimension: int = int(os.getenv("MAX_IMAGE_DIM", "2048"))
    timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "300.0"))
    
    # Web Server (Default 8030 to avoid collisions)
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8030"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
