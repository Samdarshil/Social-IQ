.PHONY: trending install dev-backend dev-frontend test typecheck build doctor e2e docker clean
install:        ## install backend + frontend dependencies
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install
dev-backend:    ## API on :8000
	cd backend && uvicorn app.main:app --reload --port 8000
dev-frontend:   ## web app on :5173 (proxies /api to :8000)
	cd frontend && npm run dev
test:           ## backend tests (no credentials needed)
	cd backend && pytest -q
typecheck:
	cd frontend && npx tsc -b
build:
	cd frontend && npm run build
trending:       ## rebuild clustering snapshots from Kaggle CSVs in backend/data/kaggle_youtube/
	python scripts/build_trending_snapshots.py
doctor:         ## show which integrations are configured; add LIVE=1 to call the real Gemini API
	python scripts/doctor.py $(if $(LIVE),--live,)
e2e:            ## browser checks: judge walkthrough + clustering page (needs both servers running + playwright)
	cd frontend && node e2e/demo-walkthrough.cjs && node e2e/clusters.cjs
docker:
	docker compose up --build
clean:
	rm -rf frontend/dist backend/.pytest_cache backend/data
