#!/bin/sh
set -e

# Render injects $PORT; fall back to 8000 for local testing
PORT=${PORT:-8000}

# Patch the placeholder in nginx.conf with the actual port
sed -i "s/__PORT__/$PORT/g" /etc/nginx/nginx.conf

# Run supervisord (manages nginx + all 4 uvicorn services)
exec supervisord -c /etc/supervisord.conf
