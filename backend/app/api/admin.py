import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import require_parent_auth
from app.config import settings
from app.database import async_session_maker, get_db
from app.models.database import (
    ChannelSource,
    ChildProfile,
    CurriculumNode,
    CurriculumStatusEnum,
    VideoItem,
    WatchLog,
)
from app.schemas.admin import (
    ChannelSourceCreate,
    ChannelSourceOut,
    ChildProfileCreate,
    ChildProfileOut,
    ChildProfileUpdate,
    ChildStatsOut,
    CurrentTopicOut,
    DailyStatOut,
    IngestRunOut,
    SystemStatusOut,
    VideoModerationPatch,
    VideoSummaryOut,
    WatchHistoryItemOut,
)
from app.services import ingestor

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

STATS_DEFAULT_DAYS = 7


# --- Профили детей: GET остаётся публичным — им пользуется киоск-плеер
# (ProfileSelect/ChildPlayer) без пароля родительской панели. ---


@router.post("/children", response_model=ChildProfileOut, dependencies=[Depends(require_parent_auth)])
async def create_child(payload: ChildProfileCreate, db: AsyncSession = Depends(get_db)) -> ChildProfile:
    child = ChildProfile(**payload.model_dump())
    db.add(child)
    await db.commit()
    await db.refresh(child)
    return child


@router.get("/children", response_model=list[ChildProfileOut])
async def list_children(db: AsyncSession = Depends(get_db)) -> list[ChildProfile]:
    result = await db.execute(select(ChildProfile))
    return list(result.scalars().all())


@router.get("/children/{child_id}", response_model=ChildProfileOut)
async def get_child(child_id: int, db: AsyncSession = Depends(get_db)) -> ChildProfile:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return child


@router.patch(
    "/children/{child_id}", response_model=ChildProfileOut, dependencies=[Depends(require_parent_auth)]
)
async def update_child(
    child_id: int, payload: ChildProfileUpdate, db: AsyncSession = Depends(get_db)
) -> ChildProfile:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(child, field, value)
    await db.commit()
    await db.refresh(child)
    return child


@router.delete("/children/{child_id}", status_code=204, dependencies=[Depends(require_parent_auth)])
async def delete_child(child_id: int, db: AsyncSession = Depends(get_db)) -> None:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    await db.delete(child)
    await db.commit()


@router.get(
    "/children/{child_id}/stats",
    response_model=ChildStatsOut,
    dependencies=[Depends(require_parent_auth)],
)
async def get_child_stats(
    child_id: int, days: int = STATS_DEFAULT_DAYS, db: AsyncSession = Depends(get_db)
) -> ChildStatsOut:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")

    range_start = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(WatchLog).where(
            WatchLog.child_id == child_id,
            WatchLog.timestamp >= datetime.combine(range_start, time.min),
        )
    )
    logs = list(result.scalars().all())

    by_date: dict[date, list[WatchLog]] = defaultdict(list)
    for log in logs:
        by_date[log.timestamp.date()].append(log)

    daily_breakdown: list[DailyStatOut] = []
    for offset in range(days):
        day = range_start + timedelta(days=offset)
        day_logs = by_date.get(day, [])
        watched_minutes = sum(log.watched_seconds for log in day_logs) / 60
        quiz_accuracy = (
            sum(1 for log in day_logs if log.quiz_passed) / len(day_logs) if day_logs else None
        )
        daily_breakdown.append(
            DailyStatOut(stat_date=day, watched_minutes=round(watched_minutes, 1), quiz_accuracy=quiz_accuracy)
        )

    today_logs = by_date.get(date.today(), [])
    today_watched_minutes = sum(log.watched_seconds for log in today_logs) / 60
    week_watched_minutes = sum(log.watched_seconds for log in logs) / 60
    week_quiz_accuracy = sum(1 for log in logs if log.quiz_passed) / len(logs) if logs else None

    node_result = await db.execute(
        select(CurriculumNode)
        .where(CurriculumNode.child_id == child_id, CurriculumNode.status == CurriculumStatusEnum.ACTIVE)
        .order_by(CurriculumNode.id.desc())
    )
    node = node_result.scalars().first()
    current_topic = (
        CurrentTopicOut(month=node.month, week=node.week, topic=node.topic, status=node.status.value)
        if node
        else None
    )

    return ChildStatsOut(
        child_id=child_id,
        daily_limit_minutes=child.daily_limit_minutes,
        today_watched_minutes=round(today_watched_minutes, 1),
        today_remaining_minutes=max(round(child.daily_limit_minutes - today_watched_minutes, 1), 0),
        week_watched_minutes=round(week_watched_minutes, 1),
        week_quiz_accuracy=week_quiz_accuracy,
        current_topic=current_topic,
        daily_breakdown=daily_breakdown,
    )


@router.get(
    "/children/{child_id}/watch-history",
    response_model=list[WatchHistoryItemOut],
    dependencies=[Depends(require_parent_auth)],
)
async def get_watch_history(
    child_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)
) -> list[WatchHistoryItemOut]:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")

    result = await db.execute(
        select(WatchLog, VideoItem.title)
        .join(VideoItem, WatchLog.video_id == VideoItem.id)
        .where(WatchLog.child_id == child_id)
        .order_by(WatchLog.timestamp.desc())
        .limit(limit)
    )

    return [
        WatchHistoryItemOut(
            id=log.id,
            video_id=log.video_id,
            video_title=title,
            watched_seconds=log.watched_seconds,
            completed=log.completed,
            skipped=log.skipped,
            quiz_passed=log.quiz_passed,
            attempts_count=log.attempts_count,
            timestamp=log.timestamp,
        )
        for log, title in result.all()
    ]


@router.post(
    "/channels", response_model=ChannelSourceOut, dependencies=[Depends(require_parent_auth)]
)
async def create_channel(
    payload: ChannelSourceCreate, db: AsyncSession = Depends(get_db)
) -> ChannelSource:
    channel = ChannelSource(**payload.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.get(
    "/channels", response_model=list[ChannelSourceOut], dependencies=[Depends(require_parent_auth)]
)
async def list_channels(
    active_only: bool = True, db: AsyncSession = Depends(get_db)
) -> list[ChannelSource]:
    query = select(ChannelSource)
    if active_only:
        query = query.where(ChannelSource.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete(
    "/channels/{channel_id}", status_code=204, dependencies=[Depends(require_parent_auth)]
)
async def deactivate_channel(channel_id: int, db: AsyncSession = Depends(get_db)) -> None:
    channel = await db.get(ChannelSource, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = False
    await db.commit()


@router.get(
    "/videos", response_model=list[VideoSummaryOut], dependencies=[Depends(require_parent_auth)]
)
async def list_videos(
    is_approved: bool | None = None,
    age_group: int | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[VideoSummaryOut]:
    query = (
        select(VideoItem)
        .options(selectinload(VideoItem.channel))
        .order_by(VideoItem.id.desc())
        .limit(limit)
    )
    if is_approved is not None:
        query = query.where(VideoItem.is_approved.is_(is_approved))
    if age_group is not None:
        query = query.where(VideoItem.age_group == age_group)

    result = await db.execute(query)
    videos = result.scalars().all()

    return [
        VideoSummaryOut(
            id=video.id,
            title=video.title,
            source_platform=video.source_platform,
            age_group=video.age_group,
            is_approved=video.is_approved,
            rejection_reason=video.rejection_reason,
            educational_score=video.educational_score,
            topic_tags=video.topic_tags or [],
            duration_sec=video.duration_sec,
            channel_name=video.channel.channel_name if video.channel else None,
        )
        for video in videos
    ]


@router.patch(
    "/videos/{video_id}", response_model=VideoSummaryOut, dependencies=[Depends(require_parent_auth)]
)
async def moderate_video(
    video_id: int, payload: VideoModerationPatch, db: AsyncSession = Depends(get_db)
) -> VideoSummaryOut:
    video = await db.get(VideoItem, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    video.is_approved = payload.is_approved
    video.rejection_reason = payload.rejection_reason
    await db.commit()

    result = await db.execute(
        select(VideoItem).options(selectinload(VideoItem.channel)).where(VideoItem.id == video_id)
    )
    video = result.scalars().one()

    return VideoSummaryOut(
        id=video.id,
        title=video.title,
        source_platform=video.source_platform,
        age_group=video.age_group,
        is_approved=video.is_approved,
        rejection_reason=video.rejection_reason,
        educational_score=video.educational_score,
        topic_tags=video.topic_tags or [],
        duration_sec=video.duration_sec,
        channel_name=video.channel.channel_name if video.channel else None,
    )


@router.get(
    "/system-status", response_model=SystemStatusOut, dependencies=[Depends(require_parent_auth)]
)
async def get_system_status(db: AsyncSession = Depends(get_db)) -> SystemStatusOut:
    children_count = (await db.execute(select(func.count(ChildProfile.id)))).scalar_one()
    channels_count = (await db.execute(select(func.count(ChannelSource.id)))).scalar_one()
    active_channels_count = (
        await db.execute(
            select(func.count(ChannelSource.id)).where(ChannelSource.is_active.is_(True))
        )
    ).scalar_one()
    videos_total_count = (await db.execute(select(func.count(VideoItem.id)))).scalar_one()
    videos_approved_count = (
        await db.execute(select(func.count(VideoItem.id)).where(VideoItem.is_approved.is_(True)))
    ).scalar_one()

    return SystemStatusOut(
        gemini_configured=bool(settings.gemini_api_key),
        telegram_configured=bool(settings.telegram_bot_token),
        children_count=children_count,
        active_channels_count=active_channels_count,
        channels_count=channels_count,
        videos_total_count=videos_total_count,
        videos_approved_count=videos_approved_count,
        videos_rejected_count=videos_total_count - videos_approved_count,
    )


async def _run_ingestion_background() -> None:
    logger.info("Фоновый цикл ингестии запущен")
    async with async_session_maker() as db:
        try:
            stats = await ingestor.run_ingestion_cycle(db)
            logger.info("Фоновый цикл ингестии завершён: %s", stats)
        except Exception:
            logger.exception("Фоновый цикл ингестии упал с ошибкой")


@router.post(
    "/ingest/run", response_model=IngestRunOut, dependencies=[Depends(require_parent_auth)]
)
async def run_ingest(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> IngestRunOut:
    """Запускает обход белого списка каналов (yt-dlp -> модерация) в фоне.

    Без этого эндпоинта единственный способ наполнить систему видео —
    вручную запускать ingestor.py из кода; теперь родитель может
    нажать кнопку в панели. Работает в фоне (BackgroundTasks), так как
    скачивание видео и вызовы Gemini могут занимать минуты — ответ
    возвращается сразу, результат появится на вкладке «Видео» позже.
    """
    active_channels_count = (
        await db.execute(
            select(func.count(ChannelSource.id)).where(ChannelSource.is_active.is_(True))
        )
    ).scalar_one()

    if active_channels_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Нет активных каналов в белом списке — сначала добавьте канал.",
        )
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY не настроен на сервере — модерация видео невозможна.",
        )

    background_tasks.add_task(_run_ingestion_background)
    return IngestRunOut(status="started", channels_count=active_channels_count)
