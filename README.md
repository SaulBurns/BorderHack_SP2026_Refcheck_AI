# RefCheck AI

AI-powered sports officiating analysis demo for BorderHack. Users upload a short basketball clip, enter optional call details, and receive a verdict with rule-based reasoning.

Current stack:

- Frontend: Next.js
- Backend: FastAPI
- Analysis: mocked multimodal/rule comparison pipeline for demo stability

## First-Time Setup

Run these commands after cloning the repo for the first time.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run Locally

You need two terminals: one for the backend and one for the frontend.

### Terminal 1: Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- Health check: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend endpoint: `http://127.0.0.1:8000/api/analyze`

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

If port `3000` is busy:

```bash
npm run dev -- --port 3001
```

## After Pulling New Updates

After running:

```bash
git pull origin main
```

Update dependencies if package files changed.

### Backend Updates

```bash
cd backend
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

Then restart the backend:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Updates

```bash
cd frontend
npm install
npm run dev
```

If the page looks stale or styles look wrong, stop the dev server with `Ctrl + C`, then run:

```bash
rm -rf .next
npm run dev
```

Then hard refresh the browser:

```text
Cmd + Shift + R
```

## Build Check

Before demoing or deploying, run:

```bash
cd frontend
npm run build
```

This verifies the Next.js app compiles correctly.

For backend syntax/import checks:

```bash
cd backend
source venv/bin/activate
python3 -m compileall main.py rules services
```

## Common Issues

### Backend port already in use

```bash
lsof -i :8000
kill -9 PID_NUMBER
```

Then restart:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend port already in use

```bash
cd frontend
npm run dev -- --port 3001
```

### Frontend cannot reach backend

Make sure the backend is running on:

```text
http://127.0.0.1:8000
```

The frontend uses:

```text
http://localhost:8000/api/analyze
```

## Current Demo Flow

1. User opens the Next.js frontend.
2. User uploads a basketball clip.
3. Frontend sends multipart form data to FastAPI.
4. Backend saves the uploaded clip temporarily.
5. Mock analyzer selects a basketball rule.
6. Backend returns a verdict:
   - Fair Call
   - Bad Call
   - Inconclusive
7. Frontend displays confidence, cited rule, reasoning, perception details, and mock adjudicator results.

## Generated Files

These are intentionally ignored by Git:

- `frontend/.next/`
- `frontend/node_modules/`
- `backend/venv/`
- `backend/uploads/`
- Python `__pycache__/`
- logs and coverage output
