# SafeLink Frontend

This is a minimal React + Vite frontend that talks to the SafeLink backend API (FastAPI).

Quick start (from project root `e:\coreproject`):

1. Install Node and dependencies

```powershell
cd Frontend
npm install
npm run dev
```

2. Start the backend API (in another terminal)

```powershell
# from e:\coreproject
# activate your Python venv before running
uvicorn Backend.SafeLink_Backend.api:app --reload
```

3. Open `http://127.0.0.1:5173` and use the UI. The app expects the API at `http://127.0.0.1:8000` by default.
