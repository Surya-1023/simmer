"""Optional live recipe web search using Tavily."""

import logging
from typing import Any

import httpx

from app.config import TAVILY_API_KEY

logger = logging.getLogger("uvicorn.error")
TAVILY_ENDPOINT = "https://api.tavily.com/search"


def search_recipe_sources(query: str, max_results: int = 4) -> list[dict[str, str]]:
    """Return source snippets for an exact dish request; no-op without a Tavily key."""
    if not TAVILY_API_KEY:
        return []

    payload = {
        "query": f"{query} recipe ingredients measurements cooking method",
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": "text",
    }
    try:
        response = httpx.post(
            TAVILY_ENDPOINT,
            headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        sources = []
        for result in data.get("results", []):
            url = str(result.get("url") or "").strip()
            if not url.startswith(("https://", "http://")):
                continue
            content = str(result.get("raw_content") or result.get("content") or "").strip()
            if not content:
                continue
            sources.append({
                "title": str(result.get("title") or "Recipe reference")[:180],
                "url": url,
                "content": content[:5000],
            })
        return sources
    except Exception as error:
        logger.warning("Live recipe search unavailable (%s). Continuing with Simmer recipe generation.", type(error).__name__)
        return []
