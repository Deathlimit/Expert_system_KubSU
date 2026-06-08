# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src/ ./src/

ENV VITE_API_BASE=
ENV VITE_BASE=/
RUN npm run build

# Stage 2: Runtime
FROM python:3.11-alpine

WORKDIR /app

COPY backend/requirements.txt .
RUN apk add --no-cache nginx \
    && pip install --no-cache-dir --no-compile \
        supervisor \
        -r requirements.txt

COPY backend/ /app/
COPY --from=frontend-builder /frontend/dist /app/frontend
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf
COPY --chmod=755 start.sh /start.sh

RUN sed -i 's/\r$//' /etc/nginx/nginx.conf /etc/supervisord.conf /start.sh

EXPOSE 8000
CMD ["/start.sh"]
