"""Параметры сборки запроса к LLM.

Здесь НЕТ нейросети: Render только собирает тело `/api/chat` и разбирает
ответ. Сам запрос выполняет домашний воркер (Ollama), поэтому значения
ниже описывают контракт, а не работу модели на сервере.
"""

import os

# Модель, которую увидит домашний воркер по умолчанию. Воркер может
# переопределить её своим OLLAMA_MODEL — тело запроса он всё равно правит.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:12b")
# Сколько ошибок максимум попадает в промпт.
LLM_MAX_ERRORS = int(os.environ.get("LLM_MAX_ERRORS", "30"))
# Контекст модели (нужен, если включено рассуждение).
LLM_NUM_CTX = int(os.environ.get("LLM_NUM_CTX", "8192"))
# Лимит ответа модели.
LLM_NUM_PREDICT = int(os.environ.get("LLM_NUM_PREDICT", "4096"))
# "false" отключает рассуждение. По умолчанию ВЫКЛЮЧЕНО: замеры показали,
# что рассуждение не улучшает портрет, а у gemma4:12b даёт пустой content.
LLM_THINK = os.environ.get("LLM_THINK", "false").strip().casefold() in ("true", "1", "yes", "on")
