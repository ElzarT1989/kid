"""Контент-парсер (Этап 2).

Обходит белый список каналов (ChannelSource) через yt-dlp: получает
свежие видео, извлекает субтитры/метаданные и — в отличие от исходной
PDF-спеки — скачивает одобренные ролики локально в VIDEO_STORAGE_PATH
(VideoItem.local_video_path), а не кэширует "живые" HLS/MP4 ссылки,
которые протухают за часы, тогда как между модерацией и показом по
плану может пройти недели.

Оркестрация пайплайна (запрос видео -> модерация -> сохранение) живёт
здесь, а не в moderator.py, чтобы moderator.py оставался чистым
LLM-сервисом без знания о БД/файловой системе.
"""

import asyncio
import logging
import re
import urllib.request
from pathlib import Path

import yt_dlp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import ChannelSource, PlatformEnum, QuizQuestion, VideoItem
from app.services import moderator, tts

logger = logging.getLogger(__name__)

MAX_NEW_VIDEOS_PER_CHANNEL = 10
SUBTITLE_LANG = "ru"


def _channel_url(channel: ChannelSource) -> str:
    if channel.platform == PlatformEnum.YOUTUBE:
        cid = channel.external_id
        if cid.startswith("http"):
            return cid
        if cid.startswith("@"):
            return f"https://www.youtube.com/{cid}/videos"
        if cid.startswith("UC"):
            return f"https://www.youtube.com/channel/{cid}/videos"
        return f"https://www.youtube.com/@{cid}/videos"
    if channel.platform == PlatformEnum.VK:
        return channel.external_id if channel.external_id.startswith("http") else f"https://vk.com/{channel.external_id}"
    raise ValueError(f"Неподдерживаемая платформа: {channel.platform}")


def _video_url(platform: PlatformEnum, external_id: str) -> str:
    if platform == PlatformEnum.YOUTUBE:
        return f"https://www.youtube.com/watch?v={external_id}"
    if platform == PlatformEnum.VK:
        return external_id if external_id.startswith("http") else f"https://vk.com/video{external_id}"
    raise ValueError(f"Неподдерживаемая платформа: {platform}")


class _YtDlpLogger:
    """quiet=True/no_warnings=True глушат вывод yt-dlp в stdout/stderr —
    без этого перехватчика причина "0 видео" (неверный URL канала,
    географическая блокировка, устаревший yt-dlp и т.п.) нигде не видна."""

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        logger.warning("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        logger.error("yt-dlp: %s", msg)


# extract_flat (список видео канала) отрабатывает и без этого — не требует
# полного "player"-ответа. А вот полная выдача метаданных ролика (формат,
# субтитры) с дефолтным клиентом "web" на дата-центровском IP (Railway)
# упирается в PO Token-проверку YouTube и возвращает ошибку для абсолютно
# всех видео подряд, даже реально доступных — признак блокировки по
# клиенту/IP, а не по конкретному ролику ("This video is not available",
# затем после форса клиента "tv" — "The page needs to be reloaded", см.
# логи Этапа 2). Перечисляем несколько альтернативных клиентов — yt-dlp
# перебирает их и использует первый сработавший; какой из них YouTube не
# блокирует, меняется от недели к неделе, поэтому расширенный список
# устойчивее одного жёстко выбранного клиента.
# Не проверено вживую: youtube.com недоступен из песочницы разработки.
_YOUTUBE_EXTRACTOR_ARGS = {"extractor_args": {"youtube": {"player_client": ["tv", "android", "ios", "web"]}}}


def _fetch_channel_video_ids_sync(channel: ChannelSource, limit: int) -> list[str]:
    url = _channel_url(channel)
    ydl_opts = {
        "extract_flat": True,
        "playlistend": limit,
        "quiet": True,
        "logger": _YtDlpLogger(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = (info or {}).get("entries") or []
    logger.info("yt-dlp URL %s -> %d entries (тип верхнего уровня: %s)", url, len(entries), (info or {}).get("_type"))
    return [entry["id"] for entry in entries if entry.get("id")]


async def fetch_channel_video_ids(channel: ChannelSource, limit: int = MAX_NEW_VIDEOS_PER_CHANNEL) -> list[str]:
    return await asyncio.to_thread(_fetch_channel_video_ids_sync, channel, limit)


def _fetch_video_metadata_sync(platform: PlatformEnum, external_id: str) -> dict:
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [SUBTITLE_LANG],
        "quiet": True,
        "no_warnings": True,
        **_YOUTUBE_EXTRACTOR_ARGS,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(_video_url(platform, external_id), download=False)


async def fetch_video_metadata(platform: PlatformEnum, external_id: str) -> dict:
    return await asyncio.to_thread(_fetch_video_metadata_sync, platform, external_id)


_VTT_TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->")
_VTT_TAG_RE = re.compile(r"<[^>]+>")


def parse_vtt_to_text(vtt_content: str) -> str:
    """Превращает содержимое .vtt субтитров в чистый текст без таймкодов/тегов."""
    lines: list[str] = []
    seen_last: str | None = None
    for raw_line in vtt_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        if _VTT_TIMESTAMP_RE.match(line) or line.isdigit():
            continue
        clean = _VTT_TAG_RE.sub("", line).strip()
        if not clean:
            continue
        # yt-dlp автосубтитры часто повторяют предыдущую строку (roll-up captions)
        if clean == seen_last:
            continue
        lines.append(clean)
        seen_last = clean
    return " ".join(lines)


def _download_text_sync(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - контролируемый источник (yt-dlp)
        return response.read().decode("utf-8", errors="replace")


async def get_transcript_text(video_info: dict) -> str | None:
    subtitles = video_info.get("subtitles") or {}
    auto_captions = video_info.get("automatic_captions") or {}
    tracks = subtitles.get(SUBTITLE_LANG) or auto_captions.get(SUBTITLE_LANG)
    if not tracks:
        return None

    vtt_track = next((t for t in tracks if t.get("ext") == "vtt"), tracks[0])
    url = vtt_track.get("url")
    if not url:
        return None

    try:
        raw = await asyncio.to_thread(_download_text_sync, url)
    except Exception:
        logger.exception("Не удалось скачать субтитры")
        return None

    return parse_vtt_to_text(raw)


def _download_video_file_sync(platform: PlatformEnum, external_id: str, dest_dir: str) -> str:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = str(Path(dest_dir) / f"{external_id}.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        # moov-atom должен стоять перед mdat, иначе HTML5 <video> в браузере
        # (в т.ч. Android WebView в киоск-режиме) не может прогрессивно
        # воспроизвести файл, отдаваемый обычным GET без Range-поддержки —
        # найдено при E2E-проверке VideoPlayer.tsx на Этапе 3.
        "postprocessor_args": {"default": ["-movflags", "+faststart"]},
        "quiet": True,
        "no_warnings": True,
        **_YOUTUBE_EXTRACTOR_ARGS,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([_video_url(platform, external_id)])

    matches = sorted(Path(dest_dir).glob(f"{external_id}.*"))
    if not matches:
        raise RuntimeError(f"yt-dlp не создал файл для {external_id}")
    return str(matches[0])


async def download_video_file(platform: PlatformEnum, external_id: str, dest_dir: str | None = None) -> str:
    return await asyncio.to_thread(
        _download_video_file_sync, platform, external_id, dest_dir or settings.video_storage_path
    )


async def _process_new_video(
    db: AsyncSession, channel: ChannelSource, external_id: str, target_age: int
) -> VideoItem | None:
    try:
        info = await fetch_video_metadata(channel.platform, external_id)
    except Exception:
        logger.exception("Не удалось получить метаданные видео %s", external_id)
        return None

    transcript = await get_transcript_text(info)
    if not transcript:
        logger.info("Видео %s пропущено: нет русских субтитров", external_id)
        return None

    video = VideoItem(
        channel_id=channel.id,
        source_platform=channel.platform,
        external_id=external_id,
        title=info.get("title", external_id),
        duration_sec=int(info.get("duration") or 0),
        transcript_text=transcript,
        age_group=target_age,
        topic_tags=[],
        educational_score=0,
        is_approved=False,
    )
    db.add(video)
    await db.flush()

    await _moderate_and_finalize(db, video)
    return video


async def _moderate_and_finalize(db: AsyncSession, video: VideoItem) -> None:
    """Двухслойная модерация: текстовый слой (обязателен), затем визуальный
    (только если текстовый слой одобрил ролик) — субтитров одних
    недостаточно для отлова агрессивного монтажа/криков без текстового следа.
    """
    try:
        text_result = await moderator.moderate_transcript(video.transcript_text or "", video.age_group)
    except Exception:
        logger.exception("Ошибка текстовой модерации видео %s", video.external_id)
        video.is_approved = False
        video.rejection_reason = "Ошибка текстовой модерации"
        return

    video.transcript_summary = text_result.summary
    video.topic_tags = text_result.topics
    video.educational_score = text_result.educational_score

    if not text_result.is_approved:
        video.is_approved = False
        video.rejection_reason = text_result.rejection_reason or "Отклонено текстовым слоем модерации"
        return

    local_path: str | None = None
    try:
        local_path = await download_video_file(video.source_platform, video.external_id)
        visual_result = await moderator.moderate_visual(local_path)
    except Exception:
        logger.exception("Ошибка визуальной модерации видео %s", video.external_id)
        video.is_approved = False
        video.rejection_reason = "Ошибка визуальной модерации"
        if local_path:
            Path(local_path).unlink(missing_ok=True)
        return

    if not visual_result.is_visually_safe:
        video.is_approved = False
        video.rejection_reason = visual_result.notes or "Отклонено визуальным слоем модерации"
        Path(local_path).unlink(missing_ok=True)
        return

    video.is_approved = True
    video.rejection_reason = None
    video.local_video_path = local_path

    for quiz in text_result.quizzes:
        quiz_question = QuizQuestion(
            video_id=video.id,
            question_text=quiz.question_voice_text,
            options_json=[option.model_dump() for option in quiz.options],
            correct_option_index=quiz.correct_option_index,
        )
        db.add(quiz_question)
        await db.flush()  # нужен id квиза для имени .mp3 файла

        try:
            quiz_question.audio_tts_path = await tts.synthesize_question_audio(
                quiz_question.question_text, quiz_question.id, video.age_group
            )
        except Exception:
            logger.exception("Не удалось синтезировать TTS для квиза %s — квиз сохранён без аудио", quiz_question.id)


async def retry_moderation(db: AsyncSession, video: VideoItem) -> None:
    """Повторно прогоняет модерацию уже существующей записи VideoItem.

    Нужно для видео, отклонённых из-за бага в самом пайплайне (а не по
    содержанию) — например, партия видео, упавшая на ValidationError из-за
    старой версии google-genai (см. CLAUDE.md/логи Этапа 2): после фикса
    кода эти записи так и остаются is_approved=False навсегда, потому что
    process_channel пропускает external_id, уже присутствующие в БД, и
    повторная ингестия канала их не подхватит.
    """
    video.is_approved = False
    video.rejection_reason = None
    await _moderate_and_finalize(db, video)
    await db.commit()


async def process_channel(db: AsyncSession, channel: ChannelSource, limit: int = MAX_NEW_VIDEOS_PER_CHANNEL) -> int:
    """Обрабатывает один канал: новые видео -> модерация. Возвращает число обработанных."""
    target_age = channel.target_age_group or 5

    label = channel.channel_name or channel.external_id
    try:
        video_ids = await fetch_channel_video_ids(channel, limit)
    except Exception:
        logger.exception("Не удалось получить список видео канала %s", label)
        return 0

    logger.info("Канал %s: yt-dlp вернул %d видео", label, len(video_ids))
    if not video_ids:
        return 0

    existing_result = await db.execute(
        select(VideoItem.external_id).where(VideoItem.external_id.in_(video_ids))
    )
    existing_ids = {row[0] for row in existing_result.all()}
    new_ids = [vid for vid in video_ids if vid not in existing_ids]
    logger.info("Канал %s: %d новых видео (уже в базе: %d)", label, len(new_ids), len(existing_ids))

    processed = 0
    for external_id in new_ids:
        video = await _process_new_video(db, channel, external_id, target_age)
        if video is not None:
            processed += 1
        await db.commit()

    return processed


async def run_ingestion_cycle(db: AsyncSession) -> dict[str, int]:
    """Точка входа для APScheduler: обходит все активные каналы белого списка."""
    result = await db.execute(select(ChannelSource).where(ChannelSource.is_active.is_(True)))
    channels = list(result.scalars().all())

    stats: dict[str, int] = {}
    for channel in channels:
        label = channel.channel_name or channel.external_id
        stats[label] = await process_channel(db, channel)

    return stats
