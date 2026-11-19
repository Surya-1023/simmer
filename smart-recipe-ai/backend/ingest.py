from app.services.vector_store import store_recipes

if __name__ == "__main__":
    total = store_recipes()
    print(f"Successfully indexed {total} recipes in ChromaDB.")
