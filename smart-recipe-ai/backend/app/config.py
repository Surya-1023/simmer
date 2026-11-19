from pathlib import Path
import os
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATASET_PATH = BACKEND_DIR / "app" / "data" / "recipes.json"
CHROMA_PATH = BACKEND_DIR / "chroma_db"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
# GPT-OSS 20B is a fast, lower-cost default for short recipe explanations.
# You can override it in backend/.env with openai/gpt-oss-120b for stronger generation.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "25"))

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

PRELOAD_EMBEDDING_MODEL = os.getenv("PRELOAD_EMBEDDING_MODEL", "true").lower() in {
    "1", "true", "yes", "on"
}
RETRIEVAL_CANDIDATES = max(5, int(os.getenv("RETRIEVAL_CANDIDATES", "20")))

# Optional: enable live recipe web search. Simmer still works without this key.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
