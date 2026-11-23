# Expert System — бэкенд для Render (без нейросети)

Готовый к деплою на [Render](https://render.com) набор сервисов бэкенда.
Здесь **нет** `portrait_service` и обращений к Ollama: на free-плане Render
нет GPU и модели, поэтому генерация портрета вынесена на домашний воркер.

## Почему без нейросети

Портрет студента считает LLM (Ollama), которой нужны гигабайты VRAM. Render
такой сервис не запустит. При этом фронтенд **не ходит** в `/portraits` —
он работает через очередь:

```text
фронт  --POST /queue/tasks---------------> Render (задача queued)
воркер --GET  /queue/tasks/pending-------> Render (что в очереди)
воркер --POST /queue/tasks/{id}----------> Render (захват, payload)
воркер --POST /queue/tasks/{id} {result}-> Render (done + профиль)
фронт  --GET  /queue/tasks/{id}----------> Render (статус/результат)
```

Поэтому на Render остаются только API и очередь, а модель считает домашний ПК.
Промпт и разбор ответа по-прежнему собирает сервер (`queue_service/llm.py`) —
это обычный Python без сети, чтобы воркер не расходился с контрактом.

## Что внутри

| Каталог | Префикс | Назначение |
|---------|---------|------------|
| `auth_service/` | `/auth` | пользователи, группы, роли, JWT |
| `content_service/` | `/content` | вопросы, категории, критерии |
| `test_service/` | `/tests` | тесты, назначения, шаринг |
| `session_service/` | `/sessions` | прохождение тестов, результаты, история |
| `queue_service/` | `/queue` | очередь задач и профили студентов |
| `main.py` | — | объединяет всё в одно FastAPI-приложение |

Чего нет (и не должно быть здесь):

- `portrait_service/` — это обёртка над Ollama;
- `ollama`/`gemma`/модели, GPU-зависимости;
- воркер, который вызывает модель (он живёт дома).

`queue_service/features.py`, `llm.py`, `llm_config.py` — детерминированная
часть контракта с LLM: подсчёт фактов, промпт, нормализация ответа. Сеть
они не трогают, модель не вызывают.

## Локальный запуск

```powershell
cd backend_render
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:MONGO_URI = "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin"
$env:PORT = "8000"
uvicorn main:app --reload --port 8000
```

Проверка: `GET http://127.0.0.1:8000/health` →
`{"status":"ok","services":["auth","content","tests","sessions","queue"],"llm":"external"}`.

В combined-режиме `test_service` и `session_service` обращаются сами к себе
по `http://127.0.0.1:$PORT`, если `CONTENT_SERVICE_URL` /
`TEST_SERVICE_URL` / `SESSION_SERVICE_URL` не заданы. `PORT` поэтому важен.

## Деплой на Render

1. Создайте бесплатный кластер MongoDB Atlas (M0) и пользователя БД.
   Строка подключения:

   ```text
   mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/testing_expert?retryWrites=true&w=majority
   ```

2. Запушьте этот каталог в отдельный GitHub-репозиторий.

3. Render Dashboard → **New → Blueprint** → выберите репозиторий.
   Render прочитает `render.yaml` и создаст `expert-system-api`.

4. В переменных окружения задайте:

   | Переменная | Значение |
   |------------|----------|
   | `MONGO_URI` | строка Atlas из шага 1 |
   | `WORKER_TOKEN` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `JWT_SECRET` | Render генерирует сам |

5. После деплоя проверьте `/health` и создайте администратора:

   ```bash
   curl -X POST https://<backend>.onrender.com/auth/setup \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'
   ```

Если репозиторий — весь проект, а папка лежит внутри, добавьте сервису
`rootDir: backend_render` (в `render.yaml` есть комментарий).

## Домашний воркер

Воркеру нужен только исходящий интернет и локальная Ollama. Он берёт задачу
из `/queue`, отправляет готовый `request` в `/api/chat` и возвращает ответ.
Готовый пример лежит в основном проекте — `backend/queue_service/worker_example.py`:

```powershell
cd backend
set QUEUE_URL=https://<backend>.onrender.com
set WORKER_TOKEN=<тот же, что в Render>
set OLLAMA_URL=http://127.0.0.1:11434
set OLLAMA_MODEL=gemma4:12b
set LLM_THINK=false
python queue_service/worker_example.py
```

Один проход по очереди и выход: `python queue_service/worker_example.py --once`.

Бесплатный Render засыпает без трафика — регулярный опрос очереди воркером
как раз не даёт сервису уснуть.

## Основные маршруты

```text
POST   /auth/register, /auth/login, /auth/setup
GET    /auth/users, /auth/students, /auth/groups
GET    /content/questions, /content/categories, /content/criteria
GET    /tests, /tests/assigned/{username}
POST   /sessions/start, /sessions/{id}/answer
GET    /sessions/history, /sessions/results/test/{test_id}
POST   /queue/tasks                     (JWT) поставить профиль в очередь
GET    /queue/tasks                     (JWT) список задач
GET    /queue/tasks/pending             (X-Worker-Token) что в очереди
POST   /queue/tasks/{id}                (X-Worker-Token) захват / результат
GET    /queue/tasks/{id}                (JWT) статус и result
GET    /health
```

Результат профиля фронтенд читает из `task.result` — отдельного
`/portraits` здесь нет намеренно.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `MONGO_URI` | localhost | MongoDB (Atlas на Render) |
| `JWT_SECRET` | dev-значение | подпись JWT |
| `CORS_ORIGINS` | `*` | origins через запятую |
| `WORKER_TOKEN` | пусто | токен домашнего воркера |
| `QUEUE_LEASE_SECONDS` | `600` | возврат зависших задач |
| `QUEUE_TASK_TTL_SECONDS` | `0` | TTL завершённых задач |
| `OLLAMA_MODEL` | `gemma4:12b` | модель по умолчанию в контракте |
| `LLM_THINK` | `false` | рассуждение модели (в промпте) |
| `LLM_MAX_ERRORS` | `30` | сколько ошибок попадает в промпт |
| `LLM_NUM_CTX` | `8192` | контекст модели в запросе |
| `LLM_NUM_PREDICT` | `4096` | лимит ответа модели |
| `CONTENT_SERVICE_URL` | — | переопределение адреса content |
| `TEST_SERVICE_URL` | — | переопределение адреса tests |
| `SESSION_SERVICE_URL` | — | переопределение адреса sessions |
| `INTERNAL_BASE_URL` | — | общий адрес для self-calls |
