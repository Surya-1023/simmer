import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    FRONTEND_ORIGINS,
    GROQ_API_KEY,
    GROQ_MODEL,
    PRELOAD_EMBEDDING_MODEL,
    TAVILY_API_KEY,
)
from app.schemas.recipe import AssistantRequest, RecipeRequest
from app.services.assistant import answer_assistant_query
from app.services.embeddings import warm_up_embedding_model
from app.services.llm import build_pantry_summary, generate_recommendation

from app.services.retriever import retrieve_recipes
from app.services.vector_store import collection

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if PRELOAD_EMBEDDING_MODEL:
        try:
            logger.info("Warming up the recipe embedding model...")
            warm_up_embedding_model()
            logger.info("Recipe embedding model is ready.")
        except Exception:
            # Do not prevent the API from starting; the first search can retry loading.
            logger.exception("Embedding model warm-up failed; it will retry on first search.")
    yield


app = FastAPI(
    title="Smart Recipe AI",
    description="A RAG-powered recipe recommendation API using ChromaDB.",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def home():
    return {
        "message": "Smart Recipe AI API is running!",
        "recipes_indexed": collection.count(),
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "recipes_indexed": collection.count(),
        "llm_configured": bool(GROQ_API_KEY),
        "llm_model": GROQ_MODEL,
        "web_search_configured": bool(TAVILY_API_KEY),
    }


@app.post("/api/recommend")
def recommend(request: RecipeRequest):
    request_started = perf_counter()
    try:
        retrieval_started = perf_counter()
        recipes = retrieve_recipes(request.ingredients, top_k=5)
        retrieval_ms = round((perf_counter() - retrieval_started) * 1000, 1)

        if not recipes:
            return {
                "recipes": [],
                "recommendation": (
                    "Let’s widen the pantry search. Add one more main ingredient, "
                    "such as chicken, egg, fish, paneer or rice, and Simmer will suggest dishes."
                ),
                "ai_generated": False,
                "notice": None,
                "retrieval_ms": retrieval_ms,
            }

        generation_started = perf_counter()
        # The pantry summary is deterministic so every ingredient the user entered
        # remains visible and the model cannot silently drop or invent pantry items.
        answer = generate_recommendation(request.ingredients, recipes)
        generation_ms = round((perf_counter() - generation_started) * 1000, 1)
        ai_generated = False
        notice = None
        total_ms = round((perf_counter() - request_started) * 1000, 1)
        logger.info(
            "Recipe request completed: retrieval=%.1fms generation=%.1fms total=%.1fms",
            retrieval_ms,
            generation_ms,
            total_ms,
        )

        return {
            "recipes": recipes,
            "recommendation": answer,
            "pantry_summary": build_pantry_summary(request.ingredients, recipes),
            "ai_generated": ai_generated,
            "notice": notice,
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        }
    except Exception as error:
        logger.exception("Recipe recommendation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {type(error).__name__}. Check the backend terminal.",
        ) from error


@app.post("/api/assistant")
def assistant(request: AssistantRequest):
    """Natural-language dish discovery and full recipe details for chat."""
    try:
        result = answer_assistant_query(request.message)
        return result
    except Exception as error:
        logger.exception("Assistant query failed")
        raise HTTPException(
            status_code=500,
            detail=f"Assistant request failed: {type(error).__name__}. Check the backend terminal.",
        ) from error
