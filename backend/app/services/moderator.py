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
from google.genai import errors as genai_errors
from google.genai import types

from app.config import settings
from app.schemas.moderation import VideoModerationResultSchema, VisualModerationResultSchema

logger = logging.getLogger(__name__)

# gemini-2.5-flash больше не существует для новых проектов — Gemini API
# отвечал 404 с прямой рекомендацией переключиться на gemini-3.8-flash
# (см. логи Этапа 2). Модель мультимодальная — годится и для текстового,
# и для визуального слоя модерации.
TEXT_MODEL = "gemini-3.8-flash"
VISION_MODEL = "gemini-3.8-flash"
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


# 503 "This model is currently experiencing high demand" от Gemini —
# встречается волнами (после включения биллинга видно, что часть
# запросов проходит успешно, часть валится 503 несколько минут подряд,
# см. логи Этапа 2). SDK сам ретраит ServerError через tenacity, но
# всего пару раз за секунды. 503 не расходует квоту (в отличие от 429),
# поэтому можно позволить себе более широкое окно ретрая.
_RETRY_DELAYS_SEC = (0, 10, 20, 40, 60)

# Free tier gemini-3.8-flash: лимит 5 запросов/мин и 20/день на проект
# (google.genai.errors.ClientError 429 RESOURCE_EXHAUSTED). Несколько
# параллельных фоновых задач (пара кликов "Повторить модерацию" подряд,
# или обычный обход канала) иначе бьют в Gemini одновременно и сжигают
# дневную квоту за секунды вместо того, чтобы растянуть те же 5
# запросов на минуту — см. логи Этапа 2: несколько 429 подряд в одну
# секунду. Лок + минимальный интервал между вызовами сериализует все
# обращения к Gemini в рамках процесса (и текстовый, и визуальный слой).
_gemini_lock = asyncio.Lock()
_last_gemini_call_at = 0.0
_MIN_GEMINI_INTERVAL_SEC = 13.0  # 5/мин = 12 сек/запрос, +1 сек запаса


async def _generate_content_with_retry(**kwargs) -> types.GenerateContentResponse:
    global _last_gemini_call_at
    client = _get_client()
    last_error: genai_errors.ServerError | None = None
    for attempt, delay in enumerate(_RETRY_DELAYS_SEC, start=1):
        if delay:
            await asyncio.sleep(delay)
        async with _gemini_lock:
            wait = _MIN_GEMINI_INTERVAL_SEC - (asyncio.get_event_loop().time() - _last_gemini_call_at)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                response = await asyncio.to_thread(client.models.generate_content, **kwargs)
            except genai_errors.ServerError as exc:
                last_error = exc
                logger.warning(
                    "Gemini %s временно недоступна (попытка %d/%d): %s",
                    kwargs.get("model"),
                    attempt,
                    len(_RETRY_DELAYS_SEC),
                    exc,
                )
                continue
            finally:
                _last_gemini_call_at = asyncio.get_event_loop().time()
            return response
    assert last_error is not None
    raise last_error


async def moderate_transcript(transcript: str, target_age: int) -> VideoModerationResultSchema:
    prompt = TEXT_MODERATION_PROMPT.format(
        target_age=target_age,
        transcript=transcript[:15000],
        options_hint=_options_hint(target_age),
    )

    response = await _generate_content_with_retry(
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

    parts: list[types.Part] = [types.Part.from_bytes(data=frame, mime_type="image/jpeg") for frame in frames]
    parts.append(types.Part.from_text(text=VISUAL_MODERATION_PROMPT))

    response = await _generate_content_with_retry(
        model=VISION_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualModerationResultSchema,
        ),
    )
    return response.parsed
