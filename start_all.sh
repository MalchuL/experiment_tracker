#!/bin/bash
# Start FastAPI backend and provide instructions for frontend

# Start FastAPI in the background
echo "Starting FastAPI backend on port 8000..."
python run_backend.py &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

echo ""
echo "🚀 FastAPI backend started on http://localhost:8000"
echo "🌐 To start the frontend, run: pnpm dev"
echo "   Frontend will be available on http://localhost:5173"
echo ""

# Handle shutdown
cleanup() {
    echo "Shutting down FastAPI..."
    kill $FASTAPI_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for FastAPI
wait $FASTAPI_PID
