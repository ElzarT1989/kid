from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import ChildProfile, DailyPlaylist

router = APIRouter(prefix="/player", tags=["player"])


class PlaylistVideoOut(BaseModel):
    order_index: int
    video_id: int
    title: str
    duration_sec: int
    local_video_path: str | None


class TodayPlaylistOut(BaseModel):
    child_id: int
    playlist_date: date
    status: str
    items: list[PlaylistVideoOut]


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
                local_video_path=item.video.local_video_path,
            )
            for item in playlist.items
        ],
    )
