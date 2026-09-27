"""ИИ-модератор (Этап 2).

Чистый LLM-сервис: вызывает Gemini API со строгим выходом по Pydantic
Schema (VideoModerationResultSchema / VisualModerationResultSchema).
Ничего не знает о БД и файловой системе — оркестрацию (когда скачивать
видео, что писать в VideoItem/QuizQuestion) делает app/services/ingestor.py.

Модерация только по субтитрам недостаточна: агрессивный монтаж, крики
или мигающие эффекты не всегда отражены в тексте, поэтому здесь два
независимых слоя — текстовый (moderate_transcript) и визуальный
(moderate_visual, ffmpeg-кадры + Gemini vision). Видео одобряется, только
если оба слоя дали положительный вердикт (см. ingestor._moderate_and_finalize).
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings
from app.schemas.moderation import VideoModerationResultSchema, VisualModerationResultSchema

logger = logging.getLogger(__name__)

TEXT_MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-flash"
FRAME_SAMPLE_COUNT = 6

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY не задан в переменных окружения")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


TEXT_MODERATION_PROMPT = """\
Ты — строгий модератор образовательного видеоконтента для ребёнка {target_age} лет.

Оцени видео по субтитрам ниже. Одобряй (is_approved=true) ТОЛЬКО спокойный,
явно развивающий и полезный контент. Отклоняй, если есть хотя бы один признак:
- резкие вскрики, визги, агрессивные звуковые эффекты;
- контент типа "unboxing", реклама игрушек, демонстрация сладостей;
- признаки быстрой смены кадров / клипового монтажа в описании сюжета;
- отсутствие явной образовательной цели.

Если одобряешь — сгенерируй ровно 2 проверочных квиза по содержанию ролика,
рассчитанных на ребёнка {target_age} лет (озвучиваемый вопрос + варианты
ответов с эмодзи-иллюстрацией, {options_hint}).

Субтитры:
\"\"\"
{transcript}
\"\"\"
"""


def _options_hint(target_age: int) -> str:
    return "2 варианта" if target_age <= 3 else "3-4 варианта"


async def moderate_transcript(transcript: str, target_age: int) -> VideoModerationResultSchema:
    client = _get_client()
    prompt = TEXT_MODERATION_PROMPT.format(
        target_age=target_age,
        transcript=transcript[:15000],
        options_hint=_options_hint(target_age),
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoModerationResultSchema,
        ),
    )
    return response.parsed


def _get_duration_seconds_sync(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _extract_frames_sync(video_path: str, count: int) -> list[bytes]:
    duration = _get_duration_seconds_sync(video_path)
    interval = max(duration / (count + 1), 1.0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        pattern = str(Path(tmp_dir) / "frame_%03d.jpg")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"fps=1/{interval}",
                "-frames:v", str(count),
                pattern,
            ],
            check=True,
            capture_output=True,
        )
        return [path.read_bytes() for path in sorted(Path(tmp_dir).glob("frame_*.jpg"))]


VISUAL_MODERATION_PROMPT = """\
Перед тобой набор кадров, равномерно взятых из детского видео. Оцени
визуальный ряд: есть ли клиповый монтаж быстрее ~1.5 сек на кадр (судя по
резкости смены сцен между кадрами), мигающие/стробоскопические эффекты,
признаки резких/агрессивных звуковых эффектов (по мимике/контексту кадра).
Дай итоговый вердикт is_visually_safe.
"""


async def moderate_visual(video_local_path: str) -> VisualModerationResultSchema:
    frames = await asyncio.to_thread(_extract_frames_sync, video_local_path, FRAME_SAMPLE_COUNT)
    if not frames:
        raise RuntimeError(f"Не удалось извлечь кадры из {video_local_path}")

    client = _get_client()
    parts: list[types.Part] = [types.Part.from_bytes(data=frame, mime_type="image/jpeg") for frame in frames]
    parts.append(types.Part.from_text(text=VISUAL_MODERATION_PROMPT))

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=VISION_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualModerationResultSchema,
        ),
    )
    return response.parsed
