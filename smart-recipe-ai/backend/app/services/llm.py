"""LLM client plus deterministic pantry summaries."""

from functools import lru_cache
import re

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL, GROQ_TIMEOUT_SECONDS


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """Reuse one HTTP client and connection pool for the lifetime of the process."""
    return Groq(
        api_key=GROQ_API_KEY,
        timeout=GROQ_TIMEOUT_SECONDS,
        max_retries=1,
    )


def clean_plain_text(text: str) -> str:
    """Remove Markdown decoration so responses read as normal UI text."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "• ", text)
    return text.strip()


def build_pantry_summary(ingredients: list[str], recipes: list[dict]) -> dict:
    """Return structured, verifiable pantry facts for the UI."""
    if not recipes:
        return {}
    selected = recipes[0]
    matched = selected.get("matched_ingredients", [])
    unused = selected.get("unused_pantry_ingredients", [])
    return {
        "best_recipe": selected.get("name", "A recipe for your kitchen"),
        "primary_ingredient": selected.get("primary_ingredient"),
        "input_count": len(ingredients),
        "matched": matched,
        "unused": unused,
        "missing": selected.get("missing_ingredients", []),
        "cooking_time": selected.get("cooking_time"),
        "servings": selected.get("servings", 4),
    }


def generate_recommendation(ingredients: list[str], recipes: list[dict]) -> str:
    """Create a fact-based pantry summary; do not ask an LLM to reinterpret the input."""
    summary = build_pantry_summary(ingredients, recipes)
    if not summary:
        return "Add a few more ingredients and Simmer will look for fresh ideas."

    lines = [
        f"Simmer’s pick: {summary['best_recipe']}",
        f"Built around {summary['primary_ingredient']} and uses {len(summary['matched'])} of the {summary['input_count']} ingredients you entered." if summary.get("primary_ingredient") else f"This dish uses {len(summary['matched'])} of the {summary['input_count']} ingredients you entered.",
        f"From your list: {', '.join(summary['matched']) if summary['matched'] else 'No direct ingredient overlap'}.",
    ]
    if summary['unused']:
        lines.append(f"Also in your pantry: {', '.join(summary['unused'])}. These are not needed for this dish.")
    if summary['missing']:
        lines.append(f"You may also need: {', '.join(summary['missing'][:9])}{' and more' if len(summary['missing']) > 9 else ''}.")
    else:
        lines.append("You already have every listed ingredient for this recipe.")
    lines.append(f"Estimated cooking time: {summary['cooking_time'] or '—'} minutes.")
    return "\n".join(lines)


def generate_fallback_recommendation(ingredients: list[str], recipes: list[dict]) -> str:
    """Backward-compatible alias for the deterministic pantry summary."""
    return generate_recommendation(ingredients, recipes)
