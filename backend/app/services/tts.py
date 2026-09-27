"""Синтез речи для квиз-вопросов через edge-tts (Этап 2).

Заранее (при одобрении видео и генерации QuizQuestion) синтезирует .mp3
файл вопроса через edge-tts и сохраняет его в TTS_CACHE_PATH; путь пишется
в QuizQuestion.audio_tts_path. Плеер проигрывает готовый файл при открытии
QuizOverlay — без синтеза "на лету" во время просмотра ребёнком.
"""

import logging
from pathlib import Path

import edge_tts

from app.config import settings

logger = logging.getLogger(__name__)

# Голос по умолчанию — женский, чёткий русский голос. Возраст 2 года (короче
# и медленнее фраза) обслуживается тем же голосом с пониженным темпом.
DEFAULT_VOICE = "ru-RU-SvetlanaNeural"
YOUNGER_CHILD_RATE = "-15%"


def _voice_rate_for_age(target_age: int) -> str:
    return YOUNGER_CHILD_RATE if target_age <= 3 else "+0%"


async def synthesize_question_audio(
    question_text: str,
    quiz_id: int,
    target_age: int = 5,
    voice: str = DEFAULT_VOICE,
) -> str:
    """Синтезирует вопрос в .mp3 и возвращает путь к сохранённому файлу.

    Идемпотентно: повторный вызов с тем же quiz_id перезапишет файл, а не
    создаст дубликат (имя файла привязано к id вопроса).
    """
    cache_dir = Path(settings.tts_cache_path)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest_path = cache_dir / f"quiz_{quiz_id}.mp3"

    communicate = edge_tts.Communicate(question_text, voice, rate=_voice_rate_for_age(target_age))
    await communicate.save(str(dest_path))

    return str(dest_path)
