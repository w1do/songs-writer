# AI Song Builder — структура проекта

## Стек

```text
React (TypeScript, Vite, TailwindCSS, shadcn/ui)
   ↓
FastAPI (SQLAlchemy)
   ↓
PostgreSQL

FastAPI
   ↓
AI Provider
```

Не использовать без явной необходимости: Redis, Celery, RabbitMQ, Kafka, microservices, векторную БД, LangChain, сложную agent-архитектуру, CQRS, DDD.

## Дерево проекта

```text
text-writer/
├── GOAL.md
├── STRUCTURE.md
├── CLAUDE.md
├── AGENTS.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── app/
│   │   ├── main.py          # точка входа FastAPI, роутеры
│   │   ├── config.py        # настройки из окружения
│   │   ├── database.py      # подключение SQLAlchemy к PostgreSQL
│   │   ├── models.py        # таблицы songs и messages
│   │   ├── schemas.py       # Pydantic-схемы запросов и ответов
│   │   ├── auth.py          # приватный вход по ADMIN_EMAIL / ADMIN_PASSWORD
│   │   ├── songs.py         # CRUD песен и autosave
│   │   ├── ai.py            # эндпоинты AI-запросов
│   │   └── services/
│   │       └── ai.py        # вызовы AI-провайдера, сборка контекста песни, валидация ответа
│   ├── requirements.txt
│   └── Dockerfile
│
└── frontend/
    ├── src/
    │   ├── components/      # редактор, sidebar, панель строки, панель AI
    │   ├── pages/           # страницы приложения
    │   ├── api/             # клиент к backend
    │   ├── hooks/           # autosave и прочие хуки
    │   ├── types/           # типы данных
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    └── Dockerfile
```

Backend и frontend не переусложнять. Файл разделяется дальше только тогда, когда становится действительно большим.

## Модель данных (MVP)

Только две таблицы.

- `songs`: id (UUID), title, idea, lyrics, track_settings (JSONB), analysis (JSONB), generation_settings (JSONB), created_at, updated_at.
- `messages`: id (UUID), song_id (FK на songs), role, content, metadata (JSONB), created_at.

Отдельные таблицы для sections, lines, words, hooks, effects, styles и genres не создаются, пока они не нужны.

## Инфраструктура

- Три сервиса в Docker Compose: frontend, backend, postgres.
- Данные PostgreSQL хранятся в Docker volume.
- Запуск: `docker compose up -d --build`.
- Переменные окружения: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SESSION_SECRET`, ключ AI-провайдера. Значения в репозиторий не коммитятся, в репозитории лежит только `.env.example`.
