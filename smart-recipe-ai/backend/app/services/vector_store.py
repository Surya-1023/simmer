import json
from functools import lru_cache

import chromadb

from app.config import CHROMA_PATH, DATASET_PATH

client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name="recipes",
    metadata={"hnsw:space": "cosine"},
)


@lru_cache(maxsize=1)
def load_recipes() -> tuple[dict, ...]:
    """Read the small local recipe dataset once per process."""
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return tuple(data)


def recipe_to_document(recipe: dict) -> str:
    return (
        f"Recipe: {recipe['name']}. Cuisine: {recipe['cuisine']}. "
        f"Meal: {recipe['meal_type']}. Category: {recipe.get('category', '')}. "
        f"Region: {recipe.get('region', '')}. Tags: {', '.join(recipe.get('tags', []))}. "
        f"Aliases: {', '.join(recipe.get('aliases', []))}. "
        f"Ingredients: {', '.join(recipe['ingredients'])}. "
        f"Cooking time: {recipe['cooking_time']} minutes. "
        f"Difficulty: {recipe['difficulty']}. "
        f"Instructions: {' '.join(recipe['instructions'])}"
    )


def store_recipes() -> int:
    """Embed the full dataset in one batch and upsert it in one Chroma call."""
    from app.services.embeddings import generate_embeddings

    recipes = list(load_recipes())
    if not recipes:
        return 0

    ids = [str(recipe["id"]) for recipe in recipes]
    documents = [recipe_to_document(recipe) for recipe in recipes]
    embeddings = generate_embeddings(documents)
    metadatas = [
        {
            "name": recipe["name"],
            "cuisine": recipe["cuisine"],
            "meal_type": recipe["meal_type"],
            "ingredients": ", ".join(recipe["ingredients"]),
            "cooking_time": int(recipe["cooking_time"]),
            "difficulty": recipe["difficulty"],
            "category": recipe.get("category", ""),
            "region": recipe.get("region", ""),
        }
        for recipe in recipes
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return len(recipes)
