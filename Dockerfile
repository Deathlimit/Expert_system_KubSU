FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --no-compile -r requirements.txt

COPY auth_service ./auth_service
COPY content_service ./content_service
COPY test_service ./test_service
COPY session_service ./session_service
COPY queue_service ./queue_service
COPY main.py ./main.py

# На Render используется python-runtime (render.yaml), но образ можно
# задеплоить и как Docker-сервис.
CMD ["sh", "-c", "python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
