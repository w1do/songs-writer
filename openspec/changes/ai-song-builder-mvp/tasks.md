## 1. Инфраструктура

- [x] 1.1 Создать `docker-compose.yml` с тремя сервисами (frontend, backend, postgres) и volume для PostgreSQL; проверить через `docker compose config`, что конфигурация валидна
- [x] 1.2 Создать `.env.example` с плейсхолдерами для `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SESSION_SECRET`, ключа и имени модели AI-провайдера; проверить, что реальных секретов нет
- [x] 1.3 Создать `backend/app/config.py`, читающий настройки из переменных окружения, и `backend/app/database.py` с подключением SQLAlchemy к PostgreSQL; проверить успешное подключение к БД при старте приложения
- [x] 1.4 Создать `backend/app/models.py` с SQLAlchemy ORM-таблицами `songs` (id, title, idea, lyrics, track_settings JSONB, analysis JSONB, generation_settings JSONB, preset_id FK → presets.id ON DELETE SET NULL, created_at, updated_at), `messages` (id, song_id FK, role, content, metadata JSONB, created_at) и `presets` (id, name, genre, bpm_min, bpm_max, energy, style_prompt, negative_style_prompt, sound_scene, hooks_prompt, effects_prompt, chorus_vocal_style, description, created_at, updated_at); проверить создание таблиц в PostgreSQL
- [x] 1.5 Создать `backend/requirements.txt` и `backend/Dockerfile`; проверить сборку образа backend через `docker build`
- [x] 1.6 Создать базовый `frontend` (Vite + React + TS + Tailwind + shadcn/ui) с `package.json` и `Dockerfile`, инициализировать shadcn/ui через `shadcn` CLI (`components.json`, базовые компоненты Button/Input/Card) поверх Tailwind-конфига; проверить сборку образа frontend через `docker build`

## 2. Авторизация и CRUD песен

- [x] 2.1 Реализовать `backend/app/auth.py`: эндпоинт входа по `ADMIN_EMAIL`/`ADMIN_PASSWORD`, выдача session-cookie на основе `SESSION_SECRET`, dependency проверки сессии; покрыть тестами успешный и неуспешный вход
- [x] 2.2 Защитить все эндпоинты, кроме входа, dependency из `auth.py`; покрыть тестом доступ без сессии (401/403) и с валидной сессией
- [x] 2.3 Создать `backend/app/schemas.py` с Pydantic-схемами песни (создание с опциональным `preset_id`, чтение, автосохранение частичного обновления); проверить валидацию обязательных и опциональных полей
- [x] 2.4 Реализовать `backend/app/songs.py`: `POST /songs` (создание из idea, опционально с `preset_id`), `GET /songs/{id}` (чтение), `PATCH /songs/{id}` (автосохранение lyrics/track_settings/analysis/generation_settings/preset_id); покрыть тестами создание, чтение, частичное обновление, получение 404 для несуществующей песни и 422 для несуществующего `preset_id`
- [x] 2.5 Реализовать эндпоинт экспорта данных песни (lyrics, style/negative style/performance, generation settings); покрыть тестом формат ответа

## 3. Пресеты жанров

- [x] 3.1 Добавить в `backend/app/schemas.py` Pydantic-схемы `PresetCreate`, `PresetUpdate`, `PresetRead` с валидацией обязательных полей (`name`, `genre`), диапазона `bpm_min <= bpm_max` и опциональных полей `sound_scene`/`hooks_prompt`/`effects_prompt`/`chorus_vocal_style`; покрыть тестами валидные и невалидные данные
- [x] 3.2 Реализовать `backend/app/presets.py`: `POST /presets`, `GET /presets`, `GET /presets/{id}`, `PATCH /presets/{id}`, `DELETE /presets/{id}` поверх SQLAlchemy ORM-сессии, защищённые session-dependency из `auth.py`; покрыть тестами CRUD со всеми полями, 404 для несуществующего пресета и сохранение связанных песен после удаления пресета
- [x] 3.3 Подключить роутер `presets.py` в `backend/app/main.py`; проверить доступность эндпоинтов через OpenAPI-схему FastAPI

## 4. AI-сервис и AI-эндпоинты

- [x] 4.1 Реализовать `backend/app/services/ai.py`: OpenAI-совместимый клиент к PolzaAi с моделью `claude-haiku-5.5`, настраиваемый через `config.py`, с обработкой таймаута и ошибок сети; покрыть unit-тестом с замоканным HTTP-клиентом
- [x] 4.2 Реализовать `build_song_context(song)` в `services/ai.py`, собирающую idea/жанр/BPM/emotion/lyrics и, при наличии `preset_id`, жанр/BPM-диапазон/энергию/style-подсказки/сцену звучания/хуки/эффекты/стиль припевов связанного пресета, в контекст для промпта; покрыть тестом на песне с частичными/полными данными и с/без пресета
- [x] 4.3 Добавить в `schemas.py` строгие Pydantic-модели ответов для каждой AI-функции (анализ идеи, line-action, hook, chorus, structure suggestion, finish song, prepare track); покрыть тестами валидные и невалидные примеры ответов
- [x] 4.4 Реализовать в `services/ai.py` логирование запроса и ответа каждой AI-функции в таблицу `messages`; проверить тестом создание записей при успешном и при ошибочном вызове
- [x] 4.5 Реализовать эндпоинт `POST /songs/{id}/analyze-idea` в `backend/app/ai.py`, сохраняющий результат в `songs.analysis`; покрыть тестом успешный анализ и обработку невалидного ответа AI (без повреждения данных песни)
- [x] 4.6 Реализовать эндпоинт line-action (variants/continue/rewrite/rhyme/flow/vocal) с общим контрактом запроса/ответа; покрыть тестом каждое действие на моках AI-ответа
- [x] 4.7 Реализовать эндпоинты `create-hook` и `create-chorus`; покрыть тестом формирование нескольких вариантов
- [x] 4.8 Реализовать эндпоинт structure-suggestion; покрыть тестом возврат рекомендуемой последовательности секций
- [x] 4.9 Реализовать эндпоинт `finish-song`, возвращающий рекомендации без изменения текста песни; покрыть тестом, что lyrics песни не меняется после вызова
- [x] 4.10 Реализовать эндпоинт `prepare-track`, сохраняющий Style Prompt/Negative Style/Performance/Generation Settings в песне; покрыть тестом сохранение всех полей

## 5. Frontend: редактор и AI-действия

- [x] 5.1 Создать типы данных (`frontend/src/types`) для песни, пресета, анализа, сообщений AI-действий; проверить типизацию через `tsc --noEmit`
- [x] 5.2 Создать API-клиент (`frontend/src/api`) для auth, CRUD песен, CRUD пресетов и всех AI-эндпоинтов; проверить ручным вызовом против запущенного backend
- [ ] 5.3 Реализовать экран входа, использующий `auth`-эндпоинт, и защиту маршрутов приложения; проверить ручным сценарием входа с верными/неверными данными
- [ ] 5.4 Реализовать выбор пресета жанра при создании песни (список пресетов из API); проверить ручным сценарием создания песни с пресетом и без него
- [ ] 5.5 Реализовать редактор текста песни с отображением секций (`frontend/src/components`); проверить ручным редактированием текста с маркерами секций
- [ ] 5.6 Реализовать выделение строки и части строки с панелью AI-действий (Variants/Continue/Rewrite/Rhyme/Flow/Vocal), применяющей выбранный вариант только по действию пользователя; проверить ручным сценарием запроса и применения варианта
- [ ] 5.7 Реализовать sidebar с анализом идеи (тема, жанр, эмоция, BPM, энергия, структура, выбранный пресет) и ручным редактированием полей; проверить ручным сценарием запуска анализа идеи и редактирования поля
- [ ] 5.8 Реализовать кнопки Create Hook и Create Chorus с отображением вариантов для выбора пользователем; проверить ручным сценарием
- [ ] 5.9 Реализовать экран Finish Song с отображением рекомендаций без автоматического изменения текста; проверить ручным сценарием
- [ ] 5.10 Реализовать autosave-хук (`frontend/src/hooks`), сохраняющий lyrics/track_settings/analysis/generation_settings с индикатором статуса сохранения; проверить ручным сценарием редактирования и наблюдением индикатора
- [ ] 5.11 Реализовать под редактором три независимые кнопки copy (текст песни, style-подсказка, negative style-подсказка), берущие style/negative style из `track_settings` песни либо из связанного пресета; проверить ручным сценарием копирования каждой кнопки в буфер обмена

## 6. Frontend: Prepare Track и экспорт

- [ ] 6.1 Реализовать экран Prepare Track, отображающий Lyrics/Style Prompt/Negative Style/Performance/Generation Settings; проверить ручным сценарием открытия для песни с подготовленными и неподготовленными данными
- [ ] 6.2 Реализовать ручное редактирование Style Prompt/Negative Style/Performance/Generation Settings на экране Prepare Track с сохранением через autosave; проверить ручным сценарием
- [ ] 6.3 Реализовать кнопку экспорта всех подготовленных данных; проверить ручным сценарием экспорта

## 7. Финальная проверка

- [x] 7.1 Прогнать backend-линтер и тесты; зафиксировать результат
- [x] 7.2 Прогнать frontend-сборку и линтер; зафиксировать результат
- [x] 7.3 Выполнить `docker compose up -d --build` и убедиться, что frontend, backend и postgres поднимаются и доступны; зафиксировать результат
- [x] 7.4 Выполнить `openspec status --change "ai-song-builder-mvp"` и убедиться, что все обязательные артефакты (`done`) готовы перед остановкой и ожиданием дальнейших указаний
