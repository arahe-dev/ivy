# Alexandria Simple

This is the no-build fallback UI for dogfooding the Alexandria/D-ACCA hooks.

It is intentionally plain:

- no React;
- no Vite;
- no Node build step;
- one HTML file, one CSS file, one JS file;
- talks directly to the same hook service as the planned frontend.

## Run

From `MoME-MoCE-Exp`:

```powershell
.\alexandria-simple.cmd start
```

Open:

```text
http://127.0.0.1:8788/alexandria_simple/index.html
```

The launcher starts:

- D-ACCA hook service on `http://127.0.0.1:8766`
- static Python web server on `http://127.0.0.1:8788`

## Hooks Used

- `GET /health`
- `GET /hooks`
- `GET /memories`
- `GET /search`
- `POST /ingest`
- `POST /packet`
- `GET /proof/{route_id}`
- `POST /feedback`
- `POST /forget`

## Manual Service Start

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py serve `
  --root out\d_acca_dogfood `
  --host 127.0.0.1 `
  --port 8766 `
  --candidate-backend indexed
```

Then serve this folder however you want, or just use the launcher.
