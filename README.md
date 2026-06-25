# Expert System KubSU

Cистема тестирования для КубГУ

## Ветки

| Ветка | Описание |
|-------|----------|
| [`main`](https://github.com/Deathlimit/Expert_system_KubSU) | Главная |
| [`backend_prod`](https://github.com/Deathlimit/Expert_system_KubSU/tree/backend_prod) | Backend |
| [`frontend_web`](https://github.com/Deathlimit/Expert_system_KubSU/tree/frontend_web) | Веб-клиент на React |
| [`desktop`](https://github.com/Deathlimit/Expert_system_KubSU/tree/desktop) | Десктоп-клиент на PyQt5 |

## Архитектура

```
React / PyQt5
      │
   Nginx (:8000)
      │
  ┌────┼────┬────┐
auth cont test sess
:8001 :8002 :8003 :8004
      │
   MongoDB
```

## Технологии

- **Бэкенд:** Python, FastAPI, Uvicorn, PyJWT, PyMongo, bcrypt
- **Фронтенд:** React 19, Vite 8
- **Десктоп:** PyQt5, requests
- **Инфра:** Docker, Nginx, MongoDB 7.0

## Функции

- Регистрация и JWT-аутентификация
- Роли: admin, teacher, student, unassigned
- Банк вопросов (темы, категории)
- Предсозданные тесты с назначением студентам
- Генерация тестов по теме и проходному баллу
- Критерии оценивания (общие / по темам)
- Сессии тестирования: таймер, лимит попыток, кулдаун
- Сохранение и возобновление сессий
- Шеринг тестов по токену
- Статистика и история студента
- Тёмная и светлая тема


## Структура бэкенда (backend_prod)

- `auth_service/` — аутентификация, пользователи, группы, роли
- `content_service/` — вопросы, критерии оценивания
- `test_service/` — тесты, назначения, генерация, шеринг
- `session_service/` — сессии тестирования, ответы, статистика
