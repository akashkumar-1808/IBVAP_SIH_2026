#!/usr/bin/env bash
# ==============================================================================
# IBVAP — Production Build Script
# ==============================================================================
set -e

echo "=== IBVAP Production Build Process ==="

# 1. Upgrade pip and install Python backend dependencies
echo "Installing Python dependencies from requirements.txt..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. Build Frontend if node/npm is available in the environment
if command -v npm &> /dev/null; then
    echo "Node.js detected. Compiling React frontend console..."
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "Node.js not in environment. Verifying pre-built frontend/dist..."
fi

# 3. Verify frontend/dist exists
if [ -d "frontend/dist" ]; then
    echo "✓ frontend/dist verified."
else
    echo "ERROR: frontend/dist not found! Please compile the frontend before deploying."
    exit 1
fi

# 4. Ensure storage directories exist
mkdir -p storage/samples storage/evidence storage/runs

echo "=== IBVAP Build Complete ==="
