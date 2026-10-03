# Campus Customs Front Desk (React + Vite + TypeScript)

The dashboard for the HW5 agent team. It talks to the FastAPI backend at http://localhost:8000.

```bash
# 1) backend (from HW5/backend, venv active)
uvicorn main:app --reload --port 8000

# 2) frontend (from HW5/frontend)
npm install   # first time only
npm run dev   # http://localhost:5173
```

The backend only allows the origin `http://localhost:5173`, so Vite runs with `strictPort`. Design notes are in `output/design.md`.

- `src/api.ts`: calls to the Problem 7 routes
- `src/agents.ts`: the agent colours and emblems, and how audit events turn into each agent's live state
- `src/App.tsx`: the dashboard (ticket rail, agent floor, live feed, run summary, vault, approvals)
- `src/index.css`: the look (black and gold)
