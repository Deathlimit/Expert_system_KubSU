#!/bin/sh
set -e

PORT=${PORT:-8000}
sed -i "s/__PORT__/$PORT/g" /etc/nginx/nginx.conf
exec supervisord -c /etc/supervisord.conf
