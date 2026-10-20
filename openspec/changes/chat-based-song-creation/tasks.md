## 1. Backend

- [ ] 1.1 Добавить `songs.story` в `models.py`, `schemas.py` и ALTER при старте
- [ ] 1.2 PATCH в `songs.py` принимает `story`
- [ ] 1.3 `POST /songs/{id}/chat` в `ai.py`, контекст в `services/ai.py`, сохранение в `messages`
- [ ] 1.4 Тесты PATCH `story` и `/chat`

## 2. Frontend

- [ ] 2.1 `useSpeechInput.ts`
- [ ] 2.2 `StoryPanel.tsx` (текст, микрофон, «Изменить историю»)
- [ ] 2.3 `SongChat.tsx`
- [ ] 2.4 Переделать `SongWorkspace.tsx`: сверху текст по секциям (read-only), снизу чат; история — компактный блок
- [ ] 2.5 Удалить `LyricsEditor` и неиспользуемые панели; обновить `api/client.ts`, `types/index.ts`

## 3. Проверки

- [ ] 3.1 Backend: линтер и тесты
- [ ] 3.2 Frontend: сборка и линтер
- [ ] 3.3 `docker compose up -d --build`
