## Why

Проект AI Song Builder пока существует только в виде документации (`GOAL.md`, `STRUCTURE.md`). Нужно реализовать весь MVP одним изменением: веб-приложение, где пользователь совместно с AI (PolzaAi, модель `claude-haiku-5.5`) пишет песню от идеи до готового трека с текстом, style/performance-промптами и настройками генерации. AI выступает соавтором — только предлагает варианты, пользователь принимает решения.

## What Changes

- Создание песни из фразы/описания/черновика текста.
- Анализ идеи: тема, эмоция, жанр, BPM, энергия, рекомендуемая структура секций (редактируется вручную).
- Редактор текста песни с секциями (`[VERSE]`, `[CHORUS]` и т.д.).
- AI-действия над строкой/выделением: Variants, Continue, Rewrite, Rhyme, Flow, Vocal.
- Create Hook, Create Chorus, предложения по структуре и исполнению.
- Finish Song: финальный AI-разбор готовой песни с рекомендациями (без автоматического изменения текста).
- Prepare Track: Lyrics, Style Prompt, Negative Style, Performance, Generation Settings.
- Autosave прогресса, copy и export результатов.
- Приватная авторизация по `ADMIN_EMAIL`/`ADMIN_PASSWORD` без публичной регистрации.
- Единый AI-сервис (`backend/app/services/ai.py`) на базе PolzaAi (OpenAI-совместимый API), модель `claude-haiku-5.5`, используемый всеми AI-функциями.
- Пресеты жанров (`presets`): хранимые в БД JSON-шаблоны полного звукового стиля (жанр, диапазон BPM, энергия, style/negative style подсказки, сцена звучания, хуки, эффекты — даблы/аэры-адлибы/ревербы, голоса и стиль припевов), которые пользователь выбирает перед написанием текста; AI пишет текст с учётом выбранного стиля, пресет передаётся как контекст, а не как жёсткое ограничение.
- На странице редактора под текстом размещаются отдельные кнопки copy: текст песни, style-подсказка и negative style-подсказка — для быстрой передачи результата во внешние сервисы генерации музыки (например, SUNO).
- Инфраструктура: backend (FastAPI + SQLAlchemy ORM + PostgreSQL, таблицы `songs`/`messages`/`presets`, Pydantic-схемы валидации на всех эндпоинтах), frontend (React + Vite + TS + Tailwind + shadcn/ui), Docker Compose с тремя сервисами.

## Capabilities

### New Capabilities
- `song-management`: CRUD песни, автосохранение (`lyrics`, `track_settings`, `analysis`, `generation_settings`), export/copy.
- `auth`: приватный вход по `ADMIN_EMAIL`/`ADMIN_PASSWORD`, session-авторизация, защита всех остальных эндпоинтов.
- `ai-writing-assistant`: анализ идеи, действия над строкой (variants/continue/rewrite/rhyme/flow/vocal), create hook/chorus, structure suggestion, finish song, prepare track — через единый PolzaAi-сервис.
- `genre-presets`: CRUD пресетов жанров (`presets`), выбор пресета при создании/редактировании песни, использование пресета как контекста в AI-промптах.
- `song-editor-ui`: редактор с секциями, выделение строки/части строки, панель AI-действий, sidebar с анализом/структурой, autosave-индикатор, copy.
- `track-preparation`: экран Prepare Track (Lyrics, Style Prompt, Negative Style, Performance, Generation Settings) и export.
- `deployment`: Docker Compose сервисы (frontend, backend, postgres), переменные окружения, volume для PostgreSQL.

### Modified Capabilities
<!-- Нет существующих capabilities в проекте — все перечислены как новые. -->

## Impact

- Backend: новые модули `backend/app/{auth.py, songs.py, ai.py, presets.py, services/ai.py, models.py, schemas.py, database.py, config.py}`, таблицы `songs`, `messages` и `presets` в PostgreSQL через SQLAlchemy ORM, Pydantic-схемы для всех запросов/ответов (включая пресеты).
- Frontend: новая структура `frontend/src` согласно `STRUCTURE.md` (редактор, панели AI-действий, Prepare Track, autosave-хук, выбор пресета жанра).
- Инфраструктура: `docker-compose.yml` с тремя сервисами, `.env.example` с плейсхолдерами для ключа PolzaAi, модели, `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `SESSION_SECRET`.
- Внешняя зависимость: PolzaAi API (OpenAI-совместимый), модель `claude-haiku-5.5`.
