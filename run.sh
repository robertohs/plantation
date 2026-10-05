#!/bin/bash
set -e

# Ensure dependencies are available
if ! python3 -c "import uvicorn, fpdf, PIL, fastapi" 2>/dev/null; then
    echo "Installing required Python packages..."
    if ! which pip3 >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y -qq
        apt-get install -y -qq -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" python3-pip
    fi
    pip3 install --no-cache-dir --break-system-packages -r requirements.txt
fi

echo "Launching Plantation Uvicorn server on port 3000..."
exec python3 server.py --host 0.0.0.0 --port 3000
