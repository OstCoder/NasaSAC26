# Deployment guide

**Status: configuration prepared; no public deployment has been performed or verified.**

The supported deployment split is:

- **Frontend:** Vercel, serving the Vite static build from `frontend/`.
- **Backend:** Render, running the FastAPI application from `backend/`.

The repository includes `render.yaml` and `frontend/vercel.json` for those choices. A different Python/static host can be used, but the same environment contract applies.

## 1. Backend on Render

### Blueprint path

1. Push the repository to GitHub.
2. In Render, create a **Blueprint** from the repository. `render.yaml` defines a Python web service with `rootDir: backend`.
3. When prompted, set `LUNANAV_CORS` to the exact frontend origin, with no trailing slash. Multiple origins are comma-separated.
4. Deploy and wait for the health check at `/health`.
5. Confirm the API docs and a real endpoint:

```bash
curl -fsS https://<backend-host>/health
curl -fsS https://<backend-host>/api/config | head
curl -fsS https://<backend-host>/api/sites | head
```

The service needs no database and no API key. The default live mode uses JPL Horizons and the committed LRO/LOLA data.

### Manual path

- Runtime: Python
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Environment: `LUNANAV_CORS=https://<frontend-host>`

`LUNANAV_ROOT` is optional. The default resolves to the repository root above `backend/`, where `config/` and `data/` live.

## 2. Frontend on Vercel

1. Import the same GitHub repository into Vercel.
2. Set the **Root Directory** to `frontend`.
3. Framework preset: Vite.
4. Build command: `npm run build`; output directory: `dist`.
5. Add the environment variable:

```text
VITE_API_BASE=https://<backend-host>
```

Use the backend origin only, with no trailing slash. The frontend appends `/api/...` itself.

6. Deploy, then set the backend's `LUNANAV_CORS` to this Vercel origin and redeploy/restart the backend so CORS takes effect.

## 3. Verify the public application

Do not treat a green host status as a working deployment. Open the public URL and run the same workflow used in the acceptance matrices:

- select all three candidate sites;
- switch between 1 Dec and 11 Dec 2026;
- inspect Sun/Earth positions, timeline and metrics;
- compare two sites and the original versus delayed window;
- change a requirement and confirm the PASS/FAIL/UNDECIDED result updates;
- open the Science page and the PSR layer;
- enable the 3D terrain view;
- confirm the browser console has no errors and the API has no 5xx responses.

Then open the site in a private window and on a second device. No login should be required.

## 4. Data and fallback behavior

The public deployment carries the committed mission series, terrain references, horizon masks and PSR catalogue. Generated caches are not committed.

If JPL Horizons or Moon Trek is slow or unavailable:

- the app reports the provider failure instead of substituting values;
- **Demo data** mode is the offline fallback and is explicitly labelled synthetic;
- the local acceptance documents and precomputed mission tables in [PHASE7_FINAL_VALIDATION.md](PHASE7_FINAL_VALIDATION.md) are the backup for a live demo.

The optional tabulated ephemeris directory is intentionally absent. Do not describe it as available in a deployment unless it has been generated and committed separately.

## 5. Security and operations

- No secrets or API keys are required for the default mode.
- Keep `.env` files out of git; only `.env.example` is committed.
- Set CORS explicitly to the deployed frontend origin; do not use `*` for a public submission.
- Pin the Python version with `PYTHON_VERSION` in Render if the platform default changes.
- Record the deployment URL, commit SHA and verification date in [SUBMISSION_PACKET.md](SUBMISSION_PACKET.md) after a successful deploy.
