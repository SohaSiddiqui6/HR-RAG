# Frontend

React + TypeScript SPA for the HR-RAG assistant. Talks to the FastAPI backend
over JSON + SSE. Architecture and diagrams: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Run

```bash
npm install
npm run dev          # http://localhost:5173, proxies /api → http://localhost:8000
```

Start the backend alongside it: `cd ../backend && uv run uvicorn src.app:app`.

## Scripts

| | |
|---|---|
| `npm run dev` | Vite dev server |
| `npm run build` | typecheck + production build to `dist/` |
| `npm run typecheck` | `tsc` only |
| `npm run lint` | oxlint |
| `npm run format` | Prettier write |
| `npm run test` | Vitest |

## Layout

Feature-sliced. Each feature owns `api / components / hooks / types`; features
don't import each other — they compose in `src/app/layout/` and share `src/lib`,
`src/components/ui`, `src/components/common`.

```
src/
├── app/          providers, query client, router, error boundary, 3-pane layout
├── components/    ui/ (shadcn primitives) · common/ (Brand, Markdown, EmptyState)
├── features/
│   ├── conversations/   api · hooks · components/{chat, sidebar, escalation}
│   └── workspace/       api · hooks · components
├── lib/           api-client · sse · cn · config · format
├── hooks/         useLocalStorage · useMediaQuery
├── types/         ApiError · conversation + workspace domain types
└── styles/        globals.css (Tailwind v4 + dark theme tokens)
```

`@/*` is aliased to `src/*`.

## Config

`VITE_API_BASE_URL` (see `.env.example`) — leave empty in dev; set to an absolute
URL when the frontend is deployed separately from the API.
