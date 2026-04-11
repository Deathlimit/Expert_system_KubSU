FROM python:3.11-alpine

# Install nginx
RUN apk add --no-cache nginx

# Install supervisor via pip (avoids Alpine package naming issues)
RUN pip install --no-cache-dir supervisor

WORKDIR /app

# Copy all service source code
COPY auth_service/    /app/auth_service/
COPY content_service/ /app/content_service/
COPY test_service/    /app/test_service/
COPY session_service/ /app/session_service/

# Install all dependencies (pip deduplicates overlapping packages)
RUN pip install --no-cache-dir \
    -r /app/auth_service/requirements.txt \
    -r /app/content_service/requirements.txt \
    -r /app/test_service/requirements.txt \
    -r /app/session_service/requirements.txt \
    && find /usr/local/lib/python3.11 -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy config files and fix Windows CRLF -> Unix LF
COPY nginx.conf       /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf
COPY start.sh         /start.sh
RUN sed -i 's/\r$//' /etc/nginx/nginx.conf /etc/supervisord.conf /start.sh \
    && chmod +x /start.sh

# $PORT is injected by Render at runtime; default to 8000
EXPOSE 8000

CMD ["/start.sh"]
