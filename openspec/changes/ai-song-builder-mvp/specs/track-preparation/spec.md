## Purpose

Предоставляет экран подготовки трека, где пользователь просматривает и редактирует финальные Lyrics, Style Prompt, Negative Style, Performance-рекомендации и Generation Settings перед экспортом для дальнейшей генерации трека.

## ADDED Requirements

### Requirement: Экран Prepare Track
Интерфейс SHALL предоставлять отдельный экран, отображающий Lyrics, Style Prompt, Negative Style, Performance-рекомендации и Generation Settings, полученные от AI-функции Prepare Track.

#### Scenario: Открытие экрана подготовки трека
- **WHEN** пользователь переходит на экран Prepare Track для песни с уже сформированными данными подготовки
- **THEN** интерфейс отображает Lyrics, Style Prompt, Negative Style, Performance-рекомендации и Generation Settings

#### Scenario: Запрос подготовки для песни без данных
- **WHEN** пользователь открывает экран Prepare Track для песни, по которой ещё не выполнялась подготовка
- **THEN** интерфейс предлагает запустить формирование этих данных через AI

### Requirement: Ручное редактирование подготовленных данных
Интерфейс SHALL позволять пользователю вручную редактировать Style Prompt, Negative Style, Performance-рекомендации и Generation Settings после их генерации.

#### Scenario: Редактирование Style Prompt
- **WHEN** пользователь изменяет текст Style Prompt на экране Prepare Track
- **THEN** интерфейс сохраняет изменённое значение в `track_settings` песни

#### Scenario: Редактирование Generation Settings
- **WHEN** пользователь изменяет значение в Generation Settings
- **THEN** интерфейс сохраняет изменение в `generation_settings` песни

### Requirement: Экспорт подготовленного трека
Интерфейс SHALL предоставлять возможность экспортировать или скопировать все подготовленные данные (Lyrics, Style Prompt, Negative Style, Performance, Generation Settings) одним действием.

#### Scenario: Экспорт всех данных
- **WHEN** пользователь нажимает кнопку export на экране Prepare Track
- **THEN** интерфейс формирует и предоставляет пользователю все подготовленные данные песни в структурированном виде
