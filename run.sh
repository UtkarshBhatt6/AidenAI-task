#!/usr/bin/env bash
set -e

echo "=================================================="
echo " Starting MediTrack Appointment Reconciliation AI "
echo "=================================================="

# Check Python environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -r backend/requirements.txt
fi

# Ensure model artifact exists
if [ ! -f "backend/app/ml/artifacts/no_show_model.joblib" ]; then
    echo "Training initial ML model artifact..."
    PYTHONPATH=backend .venv/bin/python3 backend/app/ml/trainer.py
fi

# Free ports 8000 and 3000 if occupied by stale processes
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true

# Start FastAPI backend
echo "Starting FastAPI Backend on http://127.0.0.1:8000..."
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start React Frontend
echo "Starting React Frontend on http://127.0.0.1:3000..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev -- --host 127.0.0.1 --port 3000 &
FRONTEND_PID=$!
cd ..

echo "MediTrack is running!"
echo "👉 Frontend: http://127.0.0.1:3000"
echo "👉 API Docs (Swagger): http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop both services."

cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM
wait
