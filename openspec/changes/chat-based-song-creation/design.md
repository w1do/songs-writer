## Context

Сейчас песня редактируется через `LyricsEditor` и набор панелей. Стек: FastAPI + SQLAlchemy + PostgreSQL, React + TypeScript.

## Goals / Non-Goals

**Goals:** история, чат, голосовой ввод, экран из двух частей (текст сверху, чат снизу).
**Non-Goals:** обработка звука, новые таблицы, Redis/Celery/LangChain.

## Decisions

- `songs.story` Text nullable; ALTER TABLE ... ADD COLUMN IF NOT EXISTS при старте.
- `POST /songs/{id}/chat` в `ai.py`; сборка контекста в `services/ai.py`: story, тема, жанр, пресет, текущий `lyrics`, недавние сообщения.
- ИИ возвращает ответ и обновлённый `lyrics` с тегами секций (intro, verse, pre-chorus, chorus, bridge, outro); бэкенд сохраняет его сразу, без шага подтверждения.
- UI: `SongWorkspace` — сверху read-only текст по секциям, снизу `SongChat` (текст и микрофон); история — компактный блок `StoryPanel` с «Изменить историю».
- Голос: Web Speech API в хуке `useSpeechInput`, без серверной обработки.

## Risks / Trade-offs

- Web Speech API не везде → fallback на ручной ввод.
- Удаление редактора лишает ручной правки → правки идут через чат.
- ИИ сразу перезаписывает `lyrics` → ошибочную правку можно исправить новой просьбой в чате.
