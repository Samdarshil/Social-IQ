# --- build the SPA
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- API + static SPA in one image
FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist ./static
ENV SOCIALIQ_ENV=production PORT=8000
# Set JWT_SECRET, TOKEN_ENCRYPTION_KEY, FRONTEND_URL, BACKEND_URL (https) at deploy time. Mount /app/data for SQLite or set DATABASE_URL.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
