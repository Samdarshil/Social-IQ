# SocialIQ web app

React 19 + TypeScript + Vite + Tailwind CSS v4 + Motion + Recharts + Lucide.

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000
npm run build      # type-checks and builds to dist/
npx tsc -b         # type-check only
```

- `src/pages` route screens · `src/components` (ui primitives, charts, cards) · `src/layouts` app shell
- `src/hooks` auth, filters, data fetching · `src/services/api.ts` the only place that talks to the backend
- `src/types/api.ts` response types mirroring the backend · `src/animations` shared Motion variants · `src/styles` design tokens
- `e2e/` Playwright scripts: `demo-walkthrough.cjs` (10-step judge flow) and `assistant.cjs` (assistant modes).
  Run with `npm i --no-save playwright && npx playwright install chromium`.

No secrets live in the frontend. The API key for Gemini and all OAuth secrets stay on the server.
