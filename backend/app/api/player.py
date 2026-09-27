from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.database import (
    ChildProfile,
    DailyPlaylist,
    DailyPlaylistItem,
    QuizQuestion,
    VideoItem,
    WatchLog,
)

router = APIRouter(prefix="/player", tags=["player"])


def _video_url(local_video_path: str | None) -> str | None:
    return f"/media/videos/{Path(local_video_path).name}" if local_video_path else None


def _audio_url(audio_tts_path: str | None) -> str | None:
    return f"/media/tts/{Path(audio_tts_path).name}" if audio_tts_path else None


class PlaylistVideoOut(BaseModel):
    order_index: int
    video_id: int
    title: str
    duration_sec: int
    video_url: str | None


class TodayPlaylistOut(BaseModel):
    child_id: int
    playlist_date: date
    status: str
    items: list[PlaylistVideoOut]


class QuizOptionOut(BaseModel):
    label: str
    emoji: str


class QuizOut(BaseModel):
    id: int
    question_text: str
    audio_url: str | None
    options: list[QuizOptionOut]
    correct_option_index: int


class WatchLogCreate(BaseModel):
    video_id: int
    watched_seconds: int
    completed: bool = False
    skipped: bool = False
    quiz_passed: bool = False
    attempts_count: int = 1


class WatchLogOut(BaseModel):
    id: int
    child_id: int
    video_id: int
    watched_seconds: int
    completed: bool
    skipped: bool
    quiz_passed: bool
    attempts_count: int
    timestamp: datetime


@router.get("/{child_id}/today", response_model=TodayPlaylistOut)
async def get_today_playlist(child_id: int, db: AsyncSession = Depends(get_db)) -> TodayPlaylistOut:
    """Отдаёт дневной плейлист ребёнка на сегодня.

    STUB (Этап 1): читает уже существующий DailyPlaylist, если он есть.
    Автоматическая генерация плейлиста из CurriculumNode/VideoItem —
    задача Этапа 4 (app/services/curriculum.py), сейчас там только заглушка.
    """
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")

    result = await db.execute(
        select(DailyPlaylist)
        .where(DailyPlaylist.child_id == child_id, DailyPlaylist.playlist_date == date.today())
        .options(selectinload(DailyPlaylist.items).selectinload(DailyPlaylistItem.video))
    )
    playlist = result.scalars().first()

    if playlist is None:
        raise HTTPException(
            status_code=404,
            detail="Плейлист на сегодня ещё не сгенерирован (curriculum engine — Этап 4)",
        )

    return TodayPlaylistOut(
        child_id=playlist.child_id,
        playlist_date=playlist.playlist_date,
        status=playlist.status.value,
        items=[
            PlaylistVideoOut(
                order_index=item.order_index,
                video_id=item.video.id,
                title=item.video.title,
                duration_sec=item.video.duration_sec,
                video_url=_video_url(item.video.local_video_path),
            )
            for item in playlist.items
        ],
    )


@router.get("/videos/{video_id}/quizzes", response_model=list[QuizOut])
async def get_video_quizzes(video_id: int, db: AsyncSession = Depends(get_db)) -> list[QuizOut]:
    video = await db.get(VideoItem, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    result = await db.execute(select(QuizQuestion).where(QuizQuestion.video_id == video_id))
    quizzes = result.scalars().all()

    return [
        QuizOut(
            id=quiz.id,
            question_text=quiz.question_text,
            audio_url=_audio_url(quiz.audio_tts_path),
            options=[QuizOptionOut(label=o["label"], emoji=o["emoji"]) for o in quiz.options_json],
            correct_option_index=quiz.correct_option_index,
        )
        for quiz in quizzes
    ]


@router.post("/{child_id}/watch-log", response_model=WatchLogOut, status_code=201)
async def create_watch_log(
    child_id: int, payload: WatchLogCreate, db: AsyncSession = Depends(get_db)
) -> WatchLog:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")

    video = await db.get(VideoItem, payload.video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    watch_log = WatchLog(child_id=child_id, **payload.model_dump())
    db.add(watch_log)
    await db.commit()
    await db.refresh(watch_log)
    return watch_log
