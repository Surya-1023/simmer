# Simmer Backend

FastAPI + ChromaDB + Sentence Transformers + Groq.

From this folder, activate your virtual environment, install requirements, copy `.env.example` to `.env`, set `GROQ_API_KEY`, and optionally set `TAVILY_API_KEY` for live recipe source search. Run `python ingest.py` whenever `app/data/recipes.json` changes, then start the server with `uvicorn app.main:app --reload`.

See the root `README.md` for the complete setup and frontend instructions.
