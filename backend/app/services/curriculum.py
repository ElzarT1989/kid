"""Генератор годового учебного плана и адаптивности (Этап 4).

Иерархия: Годовой план -> Модуль (месяц) -> Тема (неделя) -> Дневной
плейлист (1-3 видео), персистентно сохраняемый в DailyPlaylist/
DailyPlaylistItem (не пересчитываемый на лету при каждом запросе плеера,
см. SPEC.md §8.3). Темы берутся из фиксированного педагогического плана
(curriculum_data.py), а не генерируются LLM.

Динамическая сложность по результатам квизов за неделю (WatchLog.quiz_passed
для видео, показанных под текущим CurriculumNode — см. DailyPlaylist.
curriculum_node_id):
- >=80% успеха -> текущий узел MASTERED, переход к следующей теме по плану.
- <=50% успеха -> текущий узел NEEDS_REVIEW, повтор той же темы, но с
  других видео (за счёт исключения уже показанных роликов при подборе).
- 50-80% — обычное продвижение по плану без изменения темпа.

"Неделя" здесь — не календарная, а по факту показанных дней: считается
завершённой, когда под текущим узлом сгенерировано DAYS_PER_WEEK дневных
плейлистов (устойчиво к пропущенным дням, когда ребёнок не смотрел видео).
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    ChildProfile,
    CurriculumNode,
    CurriculumStatusEnum,
    DailyPlaylist,
    DailyPlaylistItem,
    PlaylistStatusEnum,
    VideoItem,
    WatchLog,
)
from app.services.curriculum_data import get_topic, next_month_week

DAYS_PER_WEEK = 7
MASTERY_THRESHOLD = 0.8
REVIEW_THRESHOLD = 0.5
TARGET_VIDEOS_PER_DAY = {2: 2, 5: 3}
DEFAULT_VIDEOS_PER_DAY = 2


class CurriculumError(Exception):
    """Не удалось собрать дневной плейлист (например, нет одобренных видео)."""


async def _create_node(
    db: AsyncSession,
    child: ChildProfile,
    month: int,
    week: int,
    topic: str,
    target_skills: list[str],
    status: CurriculumStatusEnum,
) -> CurriculumNode:
    node = CurriculumNode(
        child_id=child.id,
        month=month,
        week=week,
        topic=topic,
        target_skills=target_skills,
        status=status,
    )
    db.add(node)
    await db.flush()
    return node


async def _count_playlists_for_node(db: AsyncSession, node: CurriculumNode) -> int:
    result = await db.execute(
        select(func.count(DailyPlaylist.id)).where(DailyPlaylist.curriculum_node_id == node.id)
    )
    return result.scalar_one()


async def calculate_node_success_rate(
    db: AsyncSession, child: ChildProfile, node: CurriculumNode
) -> float | None:
    """Доля квизов, пройденных с первой попытки, по видео, показанным под
    этим узлом. None, если под узлом ещё не было ни одного пройденного квиза
    (нельзя оценить прогресс — не блокируем продвижение в этом случае)."""
    video_ids_result = await db.execute(
        select(DailyPlaylistItem.video_id)
        .join(DailyPlaylist, DailyPlaylistItem.playlist_id == DailyPlaylist.id)
        .where(DailyPlaylist.curriculum_node_id == node.id, DailyPlaylist.child_id == child.id)
    )
    video_ids = {row[0] for row in video_ids_result.all()}
    if not video_ids:
        return None

    result = await db.execute(
        select(WatchLog.quiz_passed).where(
            WatchLog.child_id == child.id, WatchLog.video_id.in_(video_ids)
        )
    )
    passed_flags = [row[0] for row in result.all()]
    if not passed_flags:
        return None

    return sum(1 for passed in passed_flags if passed) / len(passed_flags)


async def ensure_current_node(db: AsyncSession, child: ChildProfile) -> CurriculumNode:
    """Возвращает текущий активный узел плана ребёнка, при необходимости
    создавая первый узел или продвигая план по итогам завершённой недели."""
    result = await db.execute(
        select(CurriculumNode)
        .where(CurriculumNode.child_id == child.id)
        .order_by(CurriculumNode.id.desc())
    )
    latest = result.scalars().first()

    if latest is None:
        topic, skills = get_topic(child.age, month=1, week=1)
        return await _create_node(db, child, 1, 1, topic, skills, CurriculumStatusEnum.ACTIVE)

    if latest.status != CurriculumStatusEnum.ACTIVE:
        # Не должно происходить в норме (каждый резолв сразу создаёт новый
        # ACTIVE узел), но на случай рассинхронизации — не блокируем плеер.
        return latest

    if await _count_playlists_for_node(db, latest) < DAYS_PER_WEEK:
        return latest

    success_rate = await calculate_node_success_rate(db, child, latest)
    if success_rate is None:
        # Неделя формально прошла, но квизов не было (например, видео без
        # квизов) — считаем как обычное прохождение, не задерживаем план.
        success_rate = 1.0

    if success_rate <= REVIEW_THRESHOLD:
        latest.status = CurriculumStatusEnum.NEEDS_REVIEW
        return await _create_node(
            db, child, latest.month, latest.week, latest.topic, latest.target_skills,
            CurriculumStatusEnum.ACTIVE,
        )

    latest.status = CurriculumStatusEnum.MASTERED
    next_month, next_week = next_month_week(latest.month, latest.week)
    topic, skills = get_topic(child.age, next_month, next_week)
    return await _create_node(db, child, next_month, next_week, topic, skills, CurriculumStatusEnum.ACTIVE)


async def _get_used_video_ids(db: AsyncSession, child: ChildProfile) -> set[int]:
    result = await db.execute(
        select(DailyPlaylistItem.video_id)
        .join(DailyPlaylist, DailyPlaylistItem.playlist_id == DailyPlaylist.id)
        .where(DailyPlaylist.child_id == child.id)
    )
    return {row[0] for row in result.all()}


def _topic_overlap_score(target_skills: set[str], video: VideoItem) -> int:
    tags = {str(tag).lower() for tag in (video.topic_tags or [])}
    return sum(1 for skill in target_skills for tag in tags if skill in tag or tag in skill)


async def _select_videos(
    db: AsyncSession, child: ChildProfile, node: CurriculumNode, used_video_ids: set[int]
) -> list[VideoItem]:
    """Подбирает видео на день: уже показанные ребёнку ролики не исключаются
    полностью, а лишь оттесняются в конец списка кандидатов — так плейлист
    всегда заполняется до целевого числа видео (если в базе вообще есть
    подходящие по возрасту одобренные ролики), предпочитая новый контент, но
    показывая повтор вместо пустого дня, когда свежих роликов не хватает."""
    result = await db.execute(
        select(VideoItem).where(VideoItem.is_approved.is_(True), VideoItem.age_group == child.age)
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return []

    target_skills = {skill.lower() for skill in node.target_skills}
    candidates.sort(
        key=lambda v: (v.id not in used_video_ids, _topic_overlap_score(target_skills, v), v.educational_score),
        reverse=True,
    )

    target_count = TARGET_VIDEOS_PER_DAY.get(child.age, DEFAULT_VIDEOS_PER_DAY)
    limit_seconds = child.daily_limit_minutes * 60

    selected: list[VideoItem] = []
    total_seconds = 0
    for video in candidates:
        if len(selected) >= target_count:
            break
        if selected and total_seconds + video.duration_sec > limit_seconds:
            continue
        selected.append(video)
        total_seconds += video.duration_sec

    return selected


async def _load_playlist_with_relations(db: AsyncSession, playlist_id: int) -> DailyPlaylist:
    result = await db.execute(
        select(DailyPlaylist)
        .where(DailyPlaylist.id == playlist_id)
        .options(selectinload(DailyPlaylist.items).selectinload(DailyPlaylistItem.video))
    )
    return result.scalars().one()


async def build_daily_playlist(
    db: AsyncSession, child: ChildProfile, target_date: date
) -> DailyPlaylist:
    """Возвращает дневной плейлист ребёнка на target_date, создавая его при
    необходимости. Идемпотентно: повторный вызов на ту же дату вернёт уже
    существующий плейлист, не пересоздавая его."""
    existing = await db.execute(
        select(DailyPlaylist).where(
            DailyPlaylist.child_id == child.id, DailyPlaylist.playlist_date == target_date
        )
    )
    playlist = existing.scalars().first()
    if playlist is not None:
        return await _load_playlist_with_relations(db, playlist.id)

    node = await ensure_current_node(db, child)

    used_ids = await _get_used_video_ids(db, child)
    videos = await _select_videos(db, child, node, used_ids)
    if not videos:
        raise CurriculumError(
            f"Нет одобренных видео для профиля «{child.name}» (возраст {child.age}) — "
            "нужно запустить ingestor (Этап 2) и дождаться модерации хотя бы одного ролика."
        )

    playlist = DailyPlaylist(
        child_id=child.id,
        playlist_date=target_date,
        status=PlaylistStatusEnum.ACTIVE,
        curriculum_node_id=node.id,
    )
    db.add(playlist)
    await db.flush()

    for index, video in enumerate(videos):
        db.add(DailyPlaylistItem(playlist_id=playlist.id, video_id=video.id, order_index=index))

    await db.commit()
    return await _load_playlist_with_relations(db, playlist.id)
