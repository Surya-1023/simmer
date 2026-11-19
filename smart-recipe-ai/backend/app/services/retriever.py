"""Pantry-aware recipe retrieval with main-ingredient prioritisation."""

from __future__ import annotations

import re

from app.config import RETRIEVAL_CANDIDATES
from app.services.embeddings import generate_embedding
from app.services.vector_store import collection, load_recipes

ALIASES = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "onions": "onion",
    "eggs": "egg",
    "carrots": "carrot",
    "beans": "bean",
    "chillies": "green chilli",
    "chilis": "green chilli",
    "chili": "chilli",
    "bell pepper": "capsicum",
    "bell peppers": "capsicum",
    "capsicums": "capsicum",
    "garbanzo beans": "chickpea",
    "chickpeas": "chickpea",
    "prawns": "prawn",
    "shrimps": "shrimp",
    "mushrooms": "mushroom",
    "lemons": "lemon",
    "limes": "lime",
    "spring onions": "spring onion",
}

# Order matters: the first protein the user enters is treated as the intended
# centre of the meal. Secondary proteins remain available as pantry extras.
CORE_INGREDIENTS = {
    "chicken", "egg", "mutton", "lamb", "fish", "prawn", "shrimp",
    "paneer", "tofu", "beef", "pork", "turkey", "crab",
}


def _singularize_word(word: str) -> str:
    if word in {"chillies", "berries"}:
        return word[:-3] + "y"
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 3:
        return word[:-1]
    return word


def normalize_ingredient(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", " ", value.casefold().replace("_", " "))
    text = " ".join(text.split())
    if text in ALIASES:
        return ALIASES[text]
    return " ".join(_singularize_word(token) for token in text.split())


def _tokens(value: str) -> set[str]:
    return set(normalize_ingredient(value).replace("-", " ").split())


def ingredients_match(user_item: str, recipe_item: str) -> bool:
    """Match exact ingredients and common compound names, without substring traps."""
    user = normalize_ingredient(user_item)
    recipe = normalize_ingredient(recipe_item)
    if not user or not recipe:
        return False
    if user == recipe:
        return True

    user_tokens = _tokens(user)
    recipe_tokens = _tokens(recipe)
    return bool(user_tokens and recipe_tokens and (
        user_tokens.issubset(recipe_tokens) or recipe_tokens.issubset(user_tokens)
    ))


def _is_core_ingredient(value: str) -> bool:
    return bool(_tokens(value) & CORE_INGREDIENTS)


def _semantic_scores(query: str, count: int) -> dict[str, float]:
    if count <= 0:
        return {}
    try:
        # The local catalogue is small; ask Chroma for enough candidates to rank
        # against the complete JSON catalogue rather than only its first few hits.
        result = collection.query(
            query_embeddings=[generate_embedding(query)],
            n_results=min(count, max(RETRIEVAL_CANDIDATES, 60)),
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return {
            str(recipe_id): max(0.0, min(1.0, 1.0 - float(distance)))
            for recipe_id, distance in zip(ids, distances)
        }
    except Exception:
        # Curated ingredient matching remains available if the vector index is stale.
        return {}


def retrieve_recipes(ingredients: list[str], top_k: int = 5) -> list[dict]:
    """Rank recipe candidates around the user's first main protein and pantry fit.

    The previous approach gave every protein in a pantry equal priority. For a
    basket such as chicken, rice, tomato, onion, egg, potato, that allowed Egg
    Masala to outrank chicken dishes. This version treats the first protein as
    the meal's primary ingredient and filters to recipes that use it whenever
    the catalogue contains enough relevant candidates.
    """
    clean_ingredients = list(dict.fromkeys(
        " ".join(str(item).casefold().strip().split())
        for item in ingredients
        if item and str(item).strip()
    ))
    if not clean_ingredients:
        return []

    recipes = [dict(recipe) for recipe in load_recipes()]
    if not recipes:
        return []

    user_core = [item for item in clean_ingredients if _is_core_ingredient(item)]
    primary_core = user_core[0] if user_core else None

    # Prioritise the first main protein. If the data set has no matching recipes,
    # gracefully fall back to the full catalogue rather than returning nothing.
    candidate_pool = recipes
    if primary_core:
        protein_candidates = [
            recipe for recipe in recipes
            if any(ingredients_match(primary_core, item) for item in recipe.get("ingredients", []))
        ]
        if protein_candidates:
            candidate_pool = protein_candidates

    query = "Available ingredients: " + ", ".join(clean_ingredients)
    semantic_scores = _semantic_scores(query, collection.count())
    ranked: list[dict] = []

    for recipe in candidate_pool:
        recipe_ingredients = recipe.get("ingredients", [])
        matched_user = [
            user_item for user_item in clean_ingredients
            if any(ingredients_match(user_item, recipe_item) for recipe_item in recipe_ingredients)
        ]
        if not matched_user:
            continue

        matched_recipe = [
            recipe_item for recipe_item in recipe_ingredients
            if any(ingredients_match(user_item, recipe_item) for user_item in clean_ingredients)
        ]
        missing = [
            recipe_item for recipe_item in recipe_ingredients
            if not any(ingredients_match(user_item, recipe_item) for user_item in clean_ingredients)
        ]
        unused = [item for item in clean_ingredients if item not in matched_user]

        pantry_use = len(matched_user) / max(1, len(clean_ingredients))
        recipe_coverage = len(matched_recipe) / max(1, len(recipe_ingredients))
        semantic = semantic_scores.get(str(recipe.get("id")), 0.0)

        primary_hit = bool(primary_core) and any(
            ingredients_match(primary_core, item) for item in recipe_ingredients
        )
        # When a main protein exists, it is guaranteed by candidate filtering.
        # Pantry-use is deliberately the strongest signal, followed by coverage.
        score = (0.56 * pantry_use) + (0.34 * recipe_coverage) + (0.10 * semantic)
        if primary_hit:
            score += 0.08
        score = max(0.0, min(1.0, score))

        ranked.append({
            **recipe,
            "matched_ingredients": matched_user,
            "matched_recipe_ingredients": matched_recipe,
            "unused_pantry_ingredients": unused,
            "missing_ingredients": missing,
            "ingredient_match_score": round(recipe_coverage, 3),
            "pantry_use_score": round(pantry_use, 3),
            "semantic_score": round(semantic, 3),
            "similarity_score": round(score, 3),
            "primary_ingredient": primary_core,
        })

    ranked.sort(
        key=lambda item: (
            item["similarity_score"],
            len(item["matched_ingredients"]),
            item["ingredient_match_score"],
            -int(item.get("cooking_time", 999)),
            item.get("name", ""),
        ),
        reverse=True,
    )
    return ranked[:max(1, top_k)]
