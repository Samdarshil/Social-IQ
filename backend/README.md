# SocialIQ API

FastAPI · Pydantic · SQLAlchemy (SQLite, PostgreSQL-ready) · pandas · scikit-learn · XGBoost · SHAP · google-genai.

```bash
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # docs: http://localhost:8000/docs
pytest -q                                      # no credentials needed
```

Layout: `app/api` routers (thin) · `app/services` business logic · `app/ml` pipeline · `app/integrations` platform adapters ·
`app/security` auth + crypto · `app/models` tables · `app/schemas` Pydantic · `app/services/llm` provider layer (Gemini).
Configuration: copy `.env.example` to `.env`. Everything is optional; demo mode works with nothing.
