#!/bin/bash
# Start both FastAPI backend and Express frontend

# Start FastAPI in the background
echo "Starting FastAPI backend on port 8000..."
python run_backend.py &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start the Express frontend
echo "Starting Express frontend on port 5000..."
NODE_ENV=development npx tsx server/index.ts &
EXPRESS_PID=$!

# Handle shutdown
cleanup() {
    echo "Shutting down..."
    kill $FASTAPI_PID 2>/dev/null
    kill $EXPRESS_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait $FASTAPI_PID $EXPRESS_PID
