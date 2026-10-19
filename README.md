# AI Song Builder

AI Song Builder помогает музыканту превратить мысль, несколько строк или черновик в законченный текст песни.

Приложение не пишет песню вместо человека. Оно работает как соавтор: человек придумывает, AI предлагает варианты, человек выбирает, AI докручивает, и вместе собирается финальный трек.

## Возможности

- Создание песни из одной фразы, описания настроения или готового текста.
- Анализ идеи: тема, эмоции, жанр, BPM, энергия и структура. Рекомендации можно менять вручную.
- Редактор текста с секциями вида `[VERSE]`, `[CHORUS]` и т.д. Текст редактируется вручную, AI помогает.
- Работа со строкой: варианты, продолжение, переписывание, рифмы, flow и подсказки по исполнению, в том числе для выделенного фрагмента.
- Генерация хука и припева, предложения по структуре, flow и исполнению.
- Finish Song: финальный анализ с замечаниями. Решение о применении остаётся за пользователем.
- Prepare Track: текст, стилевой промпт, negative style, performance и настройки генерации.

Жанры (Rap, Hip-Hop, Pop, R&B, Trap, Rock, Indie, Electronic и др.) используются как музыкальный контекст, а не как жёсткие ограничения.

## Стек

- Frontend: React, TypeScript, Vite, TailwindCSS, shadcn/ui
- Backend: FastAPI, SQLAlchemy, Pydantic
- База данных: PostgreSQL
- Запуск: Docker Compose (frontend, backend, postgres)

Схема взаимодействия:

```text
React (frontend)
   ↓
FastAPI (backend)
   ↓
PostgreSQL
        ↓
   AI-провайдер
```

## Структура проекта

```text
text-writer/
├── GOAL.md              # цель и MVP
├── STRUCTURE.md         # структура и модель данных
├── CLAUDE.md            # стек и правила разработки
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py      # точка входа FastAPI, роутеры
│   │   ├── config.py    # настройки из окружения
│   │   ├── database.py  # подключение SQLAlchemy к PostgreSQL
│   │   ├── models.py    # таблицы songs и messages
│   │   ├── schemas.py   # Pydantic-схемы
│   │   ├── auth.py      # вход по ADMIN_EMAIL / ADMIN_PASSWORD
│   │   ├── songs.py     # CRUD песен и autosave
│   │   ├── ai.py        # эндпоинты AI-запросов
│   │   └── services/ai.py
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── src/             # components, pages, api, hooks, types
    ├── package.json
    └── Dockerfile
```

## Быстрый старт

### Требования

- Docker и Docker Compose
- Ключ API AI-провайдера

### Настройка окружения

Скопируйте пример переменных и заполните значения:

```bash
cp .env.example .env
```

Переменные:

- `POSTGRES_PASSWORD` — пароль PostgreSQL
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — данные для приватного входа
- `SESSION_SECRET` — секрет для подписи сессий
- `COOKIE_SECURE` — передавать ли cookie только по HTTPS
- `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL` — настройки AI-провайдера

Файл `.env` не коммитится в репозиторий.

### Запуск

```bash
docker compose up -d --build
```

Будут подняты frontend, backend и postgres. Данные PostgreSQL хранятся в Docker volume.

Проверка backend:

```bash
curl http://localhost:8000/health
```

## API

Все эндпоинты песен и AI требуют активной сессии, полученной через вход.

- `POST /auth/login`, `POST /auth/logout` — вход и выход
- `GET /songs`, `POST /songs` — список и создание песни
- `GET /songs/{song_id}`, `PATCH /songs/{song_id}`, `DELETE /songs/{song_id}` — чтение, обновление и удаление песни
- `GET /songs/{song_id}/export` — экспорт песни
- `POST /songs/{song_id}/analyze-idea` — анализ идеи
- `POST /songs/{song_id}/line-action` — действие со строкой
- `POST /songs/{song_id}/continue-section` — продолжение секции
- `POST /songs/{song_id}/create-hook` — создание хука
- `POST /songs/{song_id}/create-chorus` — создание припева
- `POST /songs/{song_id}/structure-suggestion` — предложения по структуре
- `POST /songs/{song_id}/finish-song` — финальный анализ
- `POST /songs/{song_id}/prepare-track` — подготовка трека
- `GET /presets`, `POST /presets`, `GET /presets/{preset_id}`, `PATCH /presets/{preset_id}`, `DELETE /presets/{preset_id}` — пресеты
- `GET /health` — проверка работоспособности

## Модель данных

Две таблицы:

- `songs`: id, title, idea, lyrics, track_settings, analysis, generation_settings, created_at, updated_at
- `messages`: id, song_id, role, content, metadata, created_at

## Проверки

- Backend: линтер и тесты проекта
- Frontend: сборка и линтер (`npm run build`, `npm run lint`)

## Ограничения MVP

- Обработка звука не реализуется. Vocal- и performance-подсказки — только текстовые рекомендации.
- Генерация песни вместо пользователя не предусмотрена.
- Отдельные таблицы для секций, строк, хуков и жанров не создаются.

## Документация

- [GOAL.md](GOAL.md) — цель и состав MVP
- [STRUCTURE.md](STRUCTURE.md) — структура проекта
- [CLAUDE.md](CLAUDE.md) — стек и правила разработки
- [AGENTS.md](AGENTS.md) — правила для AI-агентов
