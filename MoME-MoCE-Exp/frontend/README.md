# Alexandria Frontend

This is the local dogfood UI for the D-ACCA hook service.

## Start

Start the hook service from `MoME-MoCE-Exp`:

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py serve `
  --root out\d_acca_dogfood `
  --host 127.0.0.1 `
  --port 8766 `
  --candidate-backend indexed
```

Start the frontend from this folder:

```powershell
npm run dev
```

Open `http://localhost:5173`.

## Hook Boundary

All backend calls live in `src/hooks/useAlexandriaHooks.ts`.

The UI calls:

- `GET /health`
- `GET /hooks`
- `GET /memories?limit=50&offset=0&include_text=false`
- `POST /ingest`
- `POST /packet`
- `GET /proof/{route_id}`
- `POST /feedback`

Presentation components should receive the derived view model from the hook and should not call `fetch` directly.

## Dogfood Flow

If the live service has no memories, the dashboard shows `Load dogfood memory`.

That button ingests four small Alexandria/D-ACCA records, reruns `/packet`, and should produce a visible admitted packet for:

```text
How should Alexandria connect to D-ACCA hooks?
```

The `Use`, `Reject`, and `Stale` buttons send `/feedback` ratings for the latest route.
