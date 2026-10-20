import json
import uuid
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.database import get_db
from app.models import Message, Song
from app.schemas import (
    AnalyzeIdeaResult,
    ChatAIResult,
    ChorusResult,
    ContinueSectionRequest,
    ContinueSectionResult,
    FinishSongResult,
    HookResult,
    LineActionRequest,
    LineActionResult,
    LyricsDraftResult,
    MessageRead,
    PrepareTrackResult,
    SongChatRequest,
    SongChatResponse,
    SongRead,
    StructureResult,
)
from app.services.ai import (
    AIServiceError,
    build_chat_context,
    build_song_context,
    log_message,
    parse_structured,
    request_completion,
)

router = APIRouter(prefix="/songs", dependencies=[Depends(require_session)])

ANALYZE_IDEA_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту разобрать идею песни. "
    "Ответь только JSON-объектом с полями: "
    "theme (строка), emotion (строка), genre (строка), bpm (целое 40-220), "
    "energy (число 0-1), structure (массив строк с названиями секций). "
    "Не пиши текст песни."
)

LINE_ACTION_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту править текст песни. "
    "Действие задаётся полем action: "
    "variants, continue, rewrite, rhyme, flow, vocal. "
    "Если передан selection, предлагай варианты "
    "только для этого фрагмента строки. "
    "Ответь только JSON-объектом с полями: "
    "variants (массив от 1 до 5 строк с вариантами), note (строка или null). "
    "Не меняй текст песни сам, варианты применит пользователь."
)

CONTINUE_SECTION_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту продолжить куплет или раздел песни. "
    "Поле section содержит уже написанный текст раздела. "
    "Ответь только JSON-объектом с полями: "
    "variants (массив от 1 до 5 вариантов продолжения, "
    "каждый вариант — несколько строк через перенос строки), "
    "note (строка или null). "
    "Не переписывай написанные строки и не меняй текст песни сам."
)

HOOK_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту написать хук песни. "
    "Ответь только JSON-объектом с полем "
    "variants (массив от 1 до 5 строк-вариантов хука), "
    "согласованных с темой, жанром, эмоцией и текстом."
)

CHORUS_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту написать припев песни. "
    "Ответь только JSON-объектом с полем "
    "variants (массив от 1 до 5 вариантов, каждый вариант — массив строк припева), "
    "учитывающих уже написанные куплеты, тему, жанр и эмоцию."
)

LYRICS_DRAFT_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту придумать черновик песни. "
    "Основа — поля song: идея, анализ (тема, эмоция, жанр, BPM) и preset с параметрами стиля. "
    "Ответь только JSON-объектом с полем variants "
    "(массив от 1 до 3 вариантов). Каждый вариант — полная песня целиком: "
    "структура из блоков в квадратных скобках на отдельной строке, например [INTRO], [VERSE], "
    "[PRE-CHORUS], [CHORUS], [BRIDGE], [OUTRO], в логичном порядке. "
    "Припев повторяется одинаково в каждом повторе. "
    "Каждый блок заполнен строками текста, пустых блоков и заголовков без текста не должно быть, "
    "между блоками одна пустая строка. Не используй другие квадратные скобки внутри текста. "
    "Учитывай тему, жанр, эмоцию и уже написанный текст песни, если он есть. "
    "Пиши разговорным языком, избегай клише и случайных рифм."
)

STRUCTURE_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту выстроить структуру песни. "
    "Ответь только JSON-объектом с полями: "
    "sections (массив строк с названиями секций, например VERSE, CHORUS, BRIDGE), "
    "reason (строка или null). Учитывай уже написанный текст."
)

FINISH_SONG_SYSTEM_PROMPT = (
    "Ты делаешь финальный разбор текста песни. "
    "Ответь только JSON-объектом с полем comments "
    "(массив строк с замечаниями и рекомендациями, минимум одна строка). "
    "Не переписывай текст песни."
)

PREPARE_TRACK_SYSTEM_PROMPT = (
    "Ты готовишь данные для генерации трека по тексту песни. "
    "Ответь только JSON-объектом с полями: "
    "style_prompt (строка), negative_style_prompt (строка или null), "
    "performance (строка или null), "
    "generation_settings (объект с настройками генерации, может быть пустым)."
)

CHAT_SYSTEM_PROMPT = (
    "Ты помогаешь музыканту создать текст песни в режиме диалога. "
    "Опирайся на историю песни (story), тему (idea), жанр, параметры пресета, "
    "текущий текст (lyrics) и предыдущие сообщения. "
    "Текст строится из секций с тегами на отдельной строке: "
    "[INTRO], [VERSE], [PRE-CHORUS], [CHORUS], [BRIDGE], [OUTRO]. "
    "Хуки и припевы выстраивай через [CHORUS]. "
    "Меняй только секции, которых касается просьба, остальной текст сохраняй дословно. "
    "Если просьба неясна, задай один уточняющий вопрос в reply и верни lyrics как null. "
    "Ответь только JSON-объектом с полями: "
    "reply (строка, краткий комментарий на языке пользователя), "
    "lyrics (строка с полным обновлённым текстом или null, если текст не менялся)."
)

CHAT_HISTORY_LIMIT = 20
CHAT_ATTEMPTS = 2

ModelT = TypeVar("ModelT", bound=BaseModel)


def _get_song(db: Session, song_id: uuid.UUID) -> Song:
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    return song


@router.post("/{song_id}/analyze-idea", response_model=SongRead)
def analyze_idea(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    context = build_song_context(song, song.preset)
    log_message(
        db, song, "user", "analyze-idea", {"action": "analyze-idea", "context": context}
    )
    try:
        content = request_completion(ANALYZE_IDEA_SYSTEM_PROMPT, str(context))
        result = parse_structured(content, AnalyzeIdeaResult)
    except AIServiceError as exc:
        log_message(db, song, "error", str(exc), {"action": "analyze-idea"})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    log_message(db, song, "assistant", content, {"action": "analyze-idea"})
    song.analysis = {**(song.analysis or {}), **result.model_dump()}
    db.commit()
    db.refresh(song)
    return song


def _run_ai_action(
    db: Session,
    song: Song,
    action: str,
    system_prompt: str,
    schema: type[ModelT],
    request_payload: dict | None = None,
) -> ModelT:
    context = build_song_context(song, song.preset)
    user_prompt = json.dumps(
        {"song": context, "request": request_payload or {}}, ensure_ascii=False
    )
    log_message(
        db,
        song,
        "user",
        action,
        {"action": action, "context": context, "request": request_payload},
    )
    try:
        content = request_completion(system_prompt, user_prompt)
    except AIServiceError as exc:
        log_message(db, song, "error", str(exc), {"action": action})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    try:
        result = parse_structured(content, schema)
    except AIServiceError as exc:
        log_message(
            db, song, "error", str(exc), {"action": action, "raw_response": content}
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    log_message(db, song, "assistant", content, {"action": action})
    return result


@router.post("/{song_id}/line-action", response_model=LineActionResult)
def line_action(
    song_id: uuid.UUID, payload: LineActionRequest, db: Session = Depends(get_db)
):
    song = _get_song(db, song_id)
    return _run_ai_action(
        db,
        song,
        f"line-action:{payload.action}",
        LINE_ACTION_SYSTEM_PROMPT,
        LineActionResult,
        payload.model_dump(),
    )


@router.post("/{song_id}/continue-section", response_model=ContinueSectionResult)
def continue_section(
    song_id: uuid.UUID, payload: ContinueSectionRequest, db: Session = Depends(get_db)
):
    song = _get_song(db, song_id)
    return _run_ai_action(
        db,
        song,
        "continue-section",
        CONTINUE_SECTION_SYSTEM_PROMPT,
        ContinueSectionResult,
        payload.model_dump(),
    )


@router.post("/{song_id}/create-hook", response_model=HookResult)
def create_hook(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    return _run_ai_action(db, song, "create-hook", HOOK_SYSTEM_PROMPT, HookResult)


@router.post("/{song_id}/create-chorus", response_model=ChorusResult)
def create_chorus(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    return _run_ai_action(db, song, "create-chorus", CHORUS_SYSTEM_PROMPT, ChorusResult)


@router.post("/{song_id}/draft-lyrics", response_model=LyricsDraftResult)
def draft_lyrics(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    if not song.analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сначала проанализируйте идею",
        )
    return _run_ai_action(
        db, song, "draft-lyrics", LYRICS_DRAFT_SYSTEM_PROMPT, LyricsDraftResult
    )


@router.post("/{song_id}/structure-suggestion", response_model=StructureResult)
def structure_suggestion(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    return _run_ai_action(
        db, song, "structure-suggestion", STRUCTURE_SYSTEM_PROMPT, StructureResult
    )


@router.post("/{song_id}/finish-song", response_model=FinishSongResult)
def finish_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    return _run_ai_action(
        db, song, "finish-song", FINISH_SONG_SYSTEM_PROMPT, FinishSongResult
    )


@router.post("/{song_id}/prepare-track", response_model=SongRead)
def prepare_track(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    result = _run_ai_action(
        db, song, "prepare-track", PREPARE_TRACK_SYSTEM_PROMPT, PrepareTrackResult
    )
    song.track_settings = {
        **(song.track_settings or {}),
        "style_prompt": result.style_prompt,
        "negative_style_prompt": result.negative_style_prompt,
        "performance": result.performance,
    }
    song.generation_settings = {
        **(song.generation_settings or {}),
        **result.generation_settings,
    }
    db.commit()
    db.refresh(song)
    return song


def _request_chat_result(user_prompt: str) -> tuple[str, ChatAIResult]:
    last_error: AIServiceError | None = None
    for _ in range(CHAT_ATTEMPTS):
        content = request_completion(CHAT_SYSTEM_PROMPT, user_prompt)
        try:
            return content, parse_structured(content, ChatAIResult)
        except AIServiceError as exc:
            last_error = exc
    raise last_error


@router.get("/{song_id}/messages", response_model=list[MessageRead])
def list_chat_messages(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    return db.scalars(
        select(Message)
        .where(Message.song_id == song.id, Message.role.in_(("user", "assistant")))
        .order_by(Message.created_at)
    ).all()


@router.post("/{song_id}/chat", response_model=SongChatResponse)
def chat(song_id: uuid.UUID, payload: SongChatRequest, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    history = list(
        reversed(
            db.scalars(
                select(Message)
                .where(
                    Message.song_id == song.id,
                    Message.role.in_(("user", "assistant")),
                )
                .order_by(Message.created_at.desc())
                .limit(CHAT_HISTORY_LIMIT)
            ).all()
        )
    )
    context = build_chat_context(song, song.preset, history)
    user_message = log_message(db, song, "user", payload.message, {"action": "chat"})
    user_prompt = json.dumps(
        {"song": context, "message": payload.message}, ensure_ascii=False
    )
    try:
        content, result = _request_chat_result(user_prompt)
    except AIServiceError as exc:
        log_message(db, song, "error", str(exc), {"action": "chat"})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    assistant_message = log_message(
        db,
        song,
        "assistant",
        result.reply,
        {"action": "chat", "raw_response": content},
        commit=False,
    )
    lyrics = (result.lyrics or "").strip()
    if lyrics:
        song.lyrics = lyrics
    db.commit()
    db.refresh(song)
    db.refresh(user_message)
    db.refresh(assistant_message)
    return SongChatResponse(
        reply=result.reply,
        lyrics=song.lyrics,
        messages=[user_message, assistant_message],
    )
