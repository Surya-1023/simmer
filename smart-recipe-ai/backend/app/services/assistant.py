
"""Intent-aware Simmer assistant: local recipe retrieval, optional web search, full recipes."""

import json
import logging
import re
from functools import lru_cache
from typing import Any

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.services.embeddings import generate_embedding
from app.services.recipe_search import search_recipe_sources
from app.services.vector_store import collection, load_recipes

logger = logging.getLogger("uvicorn.error")


DISCOVERY_WORDS = {
    "variety", "varieties", "different", "options", "suggest",
    "suggestions", "recommend", "recommendations", "ideas",
    "dishes", "types", "five", "5", "some", "list",
    "variations", "choices",
}

EXPLICIT_RECIPE_WORDS = {
    "procedure", "method", "steps", "ingredients", "prepare",
    "preparation", "instructions", "measurements",
}

SPELLING_FIXES = {
    r"\bpeper\b": "pepper",
    r"\bbriyani\b|\bbiriyani\b": "biryani",
    r"\bafgani\b|\bafhani\b": "afghani",
    r"\bafgan\b": "afghan",
    r"\bchiken\b|\bchikcen\b": "chicken",
    r"\bmalaai\b": "malai",
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value: str) -> str:
    value = value.casefold().replace("&", " and ")

    for pattern, replacement in SPELLING_FIXES.items():
        value = re.sub(pattern, replacement, value)

    value = re.sub(r"[^a-z0-9\s]", " ", value)

    return " ".join(value.split())


def canonicalize_request(value: str) -> str:
    result = value.strip()

    for pattern, replacement in SPELLING_FIXES.items():
        result = re.sub(
            pattern,
            replacement,
            result,
            flags=re.IGNORECASE
        )

    return result


# ============================================================
# RECIPE SEARCH HELPERS
# ============================================================

def _recipe_search_text(recipe: dict[str, Any]) -> str:
    return normalize_text(" ".join([
        recipe.get("name", ""),
        recipe.get("region", ""),
        recipe.get("cuisine", ""),
        recipe.get("category", ""),
        " ".join(recipe.get("tags", [])),
        " ".join(recipe.get("aliases", [])),
        recipe.get("description", ""),
    ]))


def _has_chicken_curry_family(query: str) -> bool:
    words = set(normalize_text(query).split())

    chicken = bool(
        words & {"chicken", "kozhi", "nattu"}
    )

    curry = bool(
        words & {
            "curry", "gravy", "kulambu",
            "kuzhambu"
        }
    )

    return chicken and curry


# ============================================================
# INTENT DETECTION
# ============================================================

def is_discovery_query(message: str) -> bool:
    """
    True  = User wants multiple dish recommendations.
    False = User wants one specific complete recipe.
    """

    q = normalize_text(message)
    words = set(q.split())

    # Explicit recipe instructions always mean one recipe.
    if words & EXPLICIT_RECIPE_WORDS or "how to" in q:
        return False

    named_styles = {
        "methi", "malai", "afghani", "afghan",
        "butter", "kadai", "karahi", "pepper",
        "garlic", "lemon", "chettinad", "kongu",
        "kerala", "andhra", "hyderabadi",
        "mughlai", "punjabi", "kolhapuri",
        "dhaba", "village", "country", "nattu",
        "coconut", "cashew", "cream", "creamy",
        "roast", "fried", "65",
    }

    # Explicit list request.
    if words & DISCOVERY_WORDS:

        # A named dish must not become a generic list.
        if not (words & named_styles):
            return True

    # The word recipe generally means one exact recipe.
    if "recipe" in words:
        return False

    # Chicken curry intent handling.
    if _has_chicken_curry_family(q):

        # Named chicken curry styles get one complete recipe.
        if words & named_styles:
            return False

        # Generic chicken curry requests can show regional variations.
        return (
            bool(
                words & {
                    "authentic",
                    "traditional",
                    "regional"
                }
            )
            or q in {
                "chicken curry",
                "chicken gravy",
                "kozhi curry",
                "kozhi kulambu",
                "chicken kulambu",
                "chicken kuzhambu",
            }
        )

    # Default: one requested dish.
    return False


# ============================================================
# EXACT RECIPE MATCHING
# ============================================================

def find_specific_recipe(
    message: str
) -> dict[str, Any] | None:

    q = normalize_text(message)

    matches = []

    for recipe in load_recipes():

        phrases = [
            recipe.get("name", ""),
            *recipe.get("aliases", [])
        ]

        for phrase in phrases:

            candidate = normalize_text(phrase)

            if candidate and re.search(
                rf"\b{re.escape(candidate)}\b",
                q
            ):
                matches.append((
                    len(candidate.split()) * 100 + len(candidate),
                    dict(recipe)
                ))

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return matches[0][1]


# ============================================================
# OUTPUT CLEANING
# ============================================================

def _plain_generated_text(value: Any) -> str:

    text = str(value or "").strip()

    text = re.sub(
        r"\*{1,2}(.*?)\*{1,2}",
        r"\1",
        text
    )

    text = re.sub(
        r"__([^_]+)__",
        r"\1",
        text
    )

    text = re.sub(
        r"(?m)^\s{0,3}#{1,6}\s*",
        "",
        text
    )

    text = re.sub(
        r"(?m)^\s*[-*]\s+",
        "",
        text
    )

    return text.replace("*", "").replace("`", "").strip()


@lru_cache(maxsize=1)
def _dynamic_groq_client():

    from app.services.llm import get_groq_client

    return get_groq_client()


def _safe_int(value: Any, default: int) -> int:

    try:
        return max(1, min(999, int(value)))

    except (TypeError, ValueError):
        return default


# ============================================================
# DISH NAME EXTRACTION
# ============================================================

def _requested_dish_name(message: str) -> str:

    value = canonicalize_request(message)

    value = re.sub(
        r"^[,\s]*(?:hey\s+)?(?:please\s+)?",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"^(?:(?:can|could|would) you\s+)?"
        r"(?:please\s+)?"
        r"(?:(?:i want|i need|i would like)\s+"
        r"(?:a recipe for\s+)?|"
        r"(?:give me|show me|make me|prepare|cook|share|tell me)\s+)",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"^(?:a|an|the)\s+",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"^(?:a detailed |authentic |traditional |home style |restaurant style )?"
        r"recipe\s+(?:for|of)\s+",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"^(?:how to (?:make|cook|prepare) )",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"\b(?:recipe|procedure|method|instructions|measurements|steps)\b",
        " ",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"\b(?:please|for me|at home|with measurements)\b",
        " ",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"[^A-Za-z0-9' -]",
        " ",
        value
    )

    value = " ".join(value.split()).strip(" -")

    return (
        value[:90].title()
        if value
        else canonicalize_request(message).title()
    )


# ============================================================
# DYNAMIC RECIPE GENERATION
# ============================================================

def generate_dynamic_recipe(
    message: str,
    related_recipes: list[dict[str, Any]],
    web_sources: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:

    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":

        logger.warning(
            "Groq key is not configured."
        )

        return None

    web_sources = web_sources or []

    # Local recipe context.
    local_context = []

    for recipe in related_recipes[:3]:

        local_context.append(
            f"{recipe.get('name')}: "
            f"{', '.join(recipe.get('ingredients', []))}. "
            f"Method: {' '.join(recipe.get('instructions', [])[:4])}"
        )

    # Web recipe context.
    web_context = []

    for index, source in enumerate(
        web_sources[:4],
        start=1
    ):

        web_context.append(
            f"Reference {index}: {source.get('title')}\n"
            f"URL: {source.get('url')}\n"
            f"Extracted recipe information: "
            f"{source.get('content', '')[:4500]}"
        )

    canonical_request = canonicalize_request(message)

    requested_dish = _requested_dish_name(
        canonical_request
    )

    style_guidance = ""

    if "afghani chicken" in normalize_text(canonical_request):

        style_guidance = (
            "Dish identity: Afghani Chicken means the familiar "
            "Indian restaurant-style mild white-marinated chicken. "
            "Use yogurt, cream, cashew, ginger-garlic, green chilli, "
            "pepper and gentle warm spices. "
            "Do not turn it into a red tomato curry. "
            "Keep the name exactly Afghani Chicken."
        )

    prompt = f"""
You are Simmer, an experienced recipe developer.

Generate the EXACT dish requested by the user.

USER REQUEST:
{canonical_request}

EXACT DISH NAME:
{requested_dish}

{style_guidance}

LIVE RECIPE REFERENCES:
{chr(10).join(web_context) if web_context else "No live references supplied. Use established culinary knowledge."}

RELATED LOCAL RECIPES:
{chr(10).join(local_context) if local_context else "None."}

Return exactly one valid JSON object.

Required structure:

{{
    "name": "Exact requested dish",
    "cuisine": "Cuisine",
    "region": "Region",
    "meal_type": "Lunch",
    "category": "main course",
    "description": "Dish description",
    "servings": 4,
    "prep_time": 20,
    "cooking_time": 35,
    "difficulty": "Medium",
    "ingredient_details": [
        {{
            "name": "ingredient",
            "quantity": "measured quantity",
            "note": "preparation note"
        }}
    ],
    "instructions": [
        "Detailed cooking instruction"
    ],
    "tips": [
        "Cooking tip"
    ],
    "substitutions": [
        "Substitution"
    ]
}}

QUALITY REQUIREMENTS:

1. Prepare the exact dish requested.
2. Never replace it with another dish.
3. Preserve its regional cooking style.
4. Include at least 8 measured ingredients.
5. Include 8 to 12 detailed cooking steps.
6. Explain heat levels and cooking times.
7. Explain what visual signs indicate each stage is ready.
8. Include marination when required.
9. Include all essential spices and aromatics.
10. Keep ingredient quantities consistent with the method.
11. Include servings, preparation time and cooking time.
12. Explain how to finish the gravy, sauce or rice.
13. For poultry, specify a safe internal temperature of 74 C / 165 F.
14. Return valid JSON only.
15. Do not use Markdown or asterisks.
16. Do not add unrelated dishes.
"""

    options: dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return valid JSON only. "
                    "Generate the exact requested dish."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.25,
        "max_completion_tokens": 4200,
        "response_format": {
            "type": "json_object"
        }
    }

    if GROQ_MODEL.startswith("openai/gpt-oss-"):

        options["reasoning_effort"] = "low"
        options["reasoning_format"] = "hidden"

    try:

        data = None

        # Retry once if the model returns incomplete JSON.
        for attempt in range(2):

            response = (
                _dynamic_groq_client()
                .chat.completions.create(**options)
            )

            choice = response.choices[0]

            content = choice.message.content or "{}"

            try:
                candidate = json.loads(content)

            except json.JSONDecodeError:
                candidate = {}

            if not isinstance(candidate, dict):
                candidate = {}

            details = candidate.get("ingredient_details")
            steps = candidate.get("instructions")

            valid_shape = (
                isinstance(details, list)
                and len(details) >= 5
                and isinstance(steps, list)
                and len(steps) >= 7
            )

            if valid_shape:

                data = candidate
                break

            logger.warning(
                "Incomplete Groq recipe: dish=%s attempt=%d "
                "finish_reason=%s ingredients=%d steps=%d",
                canonical_request,
                attempt + 1,
                getattr(choice, "finish_reason", "unknown"),
                len(details) if isinstance(details, list) else 0,
                len(steps) if isinstance(steps, list) else 0,
            )

            if attempt == 0:

                options["messages"] = [
                    *options["messages"],
                    {
                        "role": "assistant",
                        "content": content[:9000]
                    },
                    {
                        "role": "user",
                        "content": (
                            "Your previous recipe was incomplete. "
                            "Return a complete valid JSON object for "
                            "the exact same dish. Include at least "
                            "5 measured ingredients and 7 detailed "
                            "cooking steps. Do not abbreviate."
                        )
                    }
                ]

                options["max_completion_tokens"] = 5500

        if data is None:
            return None

        details = data["ingredient_details"]
        steps = data["instructions"]

        clean_details = []

        for item in details:

            if (
                not isinstance(item, dict)
                or not item.get("name")
                or not item.get("quantity")
            ):
                continue

            clean_item = {
                "name": _plain_generated_text(item["name"]),
                "quantity": _plain_generated_text(item["quantity"]),
            }

            if item.get("note"):

                clean_item["note"] = _plain_generated_text(
                    item["note"]
                )

            clean_details.append(clean_item)

        clean_steps = [
            _plain_generated_text(step)
            for step in steps
            if str(step).strip()
        ]

        if len(clean_details) < 5 or len(clean_steps) < 7:

            logger.warning(
                "Final recipe validation failed: %s",
                canonical_request
            )

            return None

        # Preserve the exact requested dish name.
        name = _plain_generated_text(
            requested_dish
            or data.get("name")
            or canonical_request.title()
        )

        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            normalize_text(name)
        ).strip("-") or "generated-recipe"

        normalized_sources = [
            {
                "title": source["title"],
                "url": source["url"]
            }
            for source in web_sources[:4]
            if (
                source.get("title")
                and source.get("url", "").startswith(
                    ("https://", "http://")
                )
            )
        ]

        return {
            "id": f"AI-{slug}",
            "name": name,
            "cuisine": _plain_generated_text(
                data.get("cuisine") or "Home-style"
            ),
            "region": _plain_generated_text(
                data.get("region") or "Regional home-style"
            ),
            "meal_type": _plain_generated_text(
                data.get("meal_type") or "Main course"
            ),
            "category": _plain_generated_text(
                data.get("category") or "main course"
            ),
            "description": _plain_generated_text(
                data.get("description")
                or f"A detailed home-style recipe for {name}."
            ),
            "servings": _safe_int(data.get("servings"), 4),
            "prep_time": _safe_int(data.get("prep_time"), 20),
            "cooking_time": _safe_int(data.get("cooking_time"), 35),
            "difficulty": _plain_generated_text(
                data.get("difficulty") or "Medium"
            ),
            "ingredient_details": clean_details,
            "ingredients": [
                item["name"] for item in clean_details
            ],
            "instructions": clean_steps,
            "tips": [
                _plain_generated_text(tip)
                for tip in (data.get("tips") or [])
                if str(tip).strip()
            ],
            "substitutions": [
                _plain_generated_text(item)
                for item in (data.get("substitutions") or [])
                if str(item).strip()
            ],
            "aliases": [],
            "tags": [],
            "matched_ingredients": [],
            "missing_ingredients": [
                item["name"] for item in clean_details
            ],
            "ai_generated": True,
            "source_type": (
                "web" if normalized_sources else "simmer"
            ),
            "source_links": normalized_sources,
        }

    except Exception:

        logger.exception(
            "Could not generate recipe: %s",
            canonical_request
        )

        return None


# ============================================================
# MULTIPLE DISH DISCOVERY
# ============================================================

def discover_recipes(
    message: str,
    limit: int = 5
) -> list[dict[str, Any]]:

    recipes = [
        dict(recipe)
        for recipe in load_recipes()
    ]

    if not recipes:
        return []

    query = normalize_text(message)

    stop_words = {
        "show", "me", "give", "please", "some",
        "suggest", "suggestions", "recommend",
        "recommendations", "find", "for", "with",
        "the", "and", "five", "5", "dishes",
        "dish", "types", "options", "ideas",
        "authentic", "traditional", "regional",
        "different", "variety", "varieties", "of",
    }

    query_words = {
        word
        for word in query.split()
        if len(word) > 2 and word not in stop_words
    }

    semantic_scores: dict[str, float] = {}

    # ChromaDB semantic retrieval.
    if collection.count():

        try:

            result = collection.query(
                query_embeddings=[
                    generate_embedding(message)
                ],
                n_results=min(
                    collection.count(),
                    max(30, limit * 6)
                ),
                include=["distances"],
            )

            for recipe_id, distance in zip(
                result.get("ids", [[]])[0],
                result.get("distances", [[]])[0]
            ):

                semantic_scores[str(recipe_id)] = max(
                    0.0,
                    min(1.0, 1.0 - float(distance))
                )

        except Exception:

            logger.exception(
                "Vector lookup failed; using catalogue search."
            )

    chicken_curry_family = _has_chicken_curry_family(query)

    if chicken_curry_family:

        candidates = [
            recipe
            for recipe in recipes
            if (
                "chicken" in _recipe_search_text(recipe)
                and (
                    recipe.get("category")
                    in {"curry", "gravy", "kulambu"}
                    or bool(
                        {"curry", "gravy", "kulambu"}
                        & set(recipe.get("tags", []))
                    )
                )
            )
        ]

        if {"authentic", "traditional", "regional"} & set(query.split()):

            candidates = [
                recipe
                for recipe in candidates
                if recipe.get("name") != "Everyday Chicken Curry"
            ]

        if len(candidates) < limit:

            extras = [
                recipe
                for recipe in recipes
                if (
                    "chicken" in _recipe_search_text(recipe)
                    and recipe not in candidates
                    and recipe.get("category")
                    in {"dry curry", "fry", "stir fry"}
                )
            ]

            candidates.extend(extras[:limit - len(candidates)])

    else:

        candidates = recipes

    ranked = []

    for recipe in candidates:

        search_words = set(
            _recipe_search_text(recipe).split()
        )

        overlap = (
            len(query_words & search_words)
            / max(1, len(query_words))
        )

        semantic = semantic_scores.get(
            str(recipe["id"]),
            0.0
        )

        score = 0.72 * overlap + 0.28 * semantic

        if chicken_curry_family:

            score += (
                0.18
                if recipe.get("category")
                in {"curry", "gravy", "kulambu"}
                else 0.0
            )

            if recipe.get("region"):
                score += 0.015

        item = dict(recipe)

        item["similarity_score"] = round(
            max(0.0, min(1.0, score)),
            3
        )

        item["matched_ingredients"] = []

        item["missing_ingredients"] = list(
            recipe.get("ingredients", [])
        )

        ranked.append((score, item))

    ranked.sort(
        key=lambda pair: (
            pair[0],
            pair[1].get("region", ""),
            pair[1].get("name", "")
        ),
        reverse=True
    )

    return [
        item
        for _, item in ranked[:max(1, limit)]
    ]


# ============================================================
# MAIN ASSISTANT ROUTER
# ============================================================

def answer_assistant_query(
    message: str
) -> dict[str, Any]:

    clean_message = canonicalize_request(
        message.strip()
    )

    # --------------------------------------------------------
    # DISCOVERY: user explicitly wants multiple dishes.
    # --------------------------------------------------------

    if is_discovery_query(clean_message):

        recipes = discover_recipes(
            clean_message,
            limit=5
        )

        if _has_chicken_curry_family(clean_message):

            intro = (
                "Here are five chicken curry styles from "
                "different kitchens. Choose one to see "
                "measured ingredients and the full cooking method."
            )

        else:

            intro = (
                "Here are five dishes to explore. "
                "Choose one to open its measured ingredients "
                "and complete cooking method."
            )

        return {
            "intent": "discover",
            "message": intro,
            "recipes": recipes,
        }

    # --------------------------------------------------------
    # EXACT MATCH: use the local recipe library first.
    # --------------------------------------------------------

    recipe = find_specific_recipe(clean_message)

    if recipe:

        recipe["similarity_score"] = 1.0

        recipe["matched_ingredients"] = []

        recipe["missing_ingredients"] = list(
            recipe.get("ingredients", [])
        )

        recipe["source_type"] = "library"

        return {
            "intent": "recipe",
            "message": (
                f"Here’s the complete {recipe['name']} recipe, "
                "with measured ingredients and a detailed "
                "step-by-step method."
            ),
            "recipes": [recipe],
            "selected_recipe": recipe,
        }

    # --------------------------------------------------------
    # DYNAMIC GENERATION: exact dish requested.
    # --------------------------------------------------------

    related = discover_recipes(
        clean_message,
        limit=3
    )

    web_sources = search_recipe_sources(
        clean_message
    )

    generated = generate_dynamic_recipe(
        clean_message,
        related,
        web_sources
    )

    if generated:

        source_sentence = (
            " I’ve included the recipe references below."
            if generated.get("source_links")
            else ""
        )

        return {
            "intent": "recipe",
            "message": (
                f"Here’s your {generated['name']} recipe, "
                "with measured ingredients, timings and "
                f"a complete cooking method.{source_sentence}"
            ),
            "recipes": [generated],
            "selected_recipe": generated,
            "ai_generated": True,
            "source_type": generated.get(
                "source_type",
                "simmer"
            ),
        }

    # --------------------------------------------------------
    # SAFE FAILURE: never substitute an unrelated dish.
    # --------------------------------------------------------

    requested_dish = _requested_dish_name(
        clean_message
    )

    return {
        "intent": "help",
        "message": (
            f"I couldn't prepare a reliable {requested_dish} "
            "recipe just now. Please try again in a moment. "
            "I haven't replaced your request with a different dish."
        ),
        "recipes": [],
    }
