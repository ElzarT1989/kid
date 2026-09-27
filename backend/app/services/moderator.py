"""ИИ-модератор (Этап 2).

Строгий фильтр контента через Gemini API со Structured Output.
В отличие от исходной PDF-спеки, модерация только по субтитрам признана
недостаточной (агрессивный монтаж, крики или мигающие эффекты не всегда
отражены в тексте) — нужен второй, визуальный слой на базе выборки кадров
через ffmpeg + Gemini vision, прежде чем этот модуль станет единственным
гейткипером контента.

TODO (Этап 2):
- moderate_transcript(transcript: str, target_age: int) -> VideoModerationResultSchema
  Вызов Gemini 2.5 Flash с response_schema=VideoModerationResultSchema.
- moderate_visual(video_local_path: str) -> VisualModerationResultSchema
  ffmpeg scene-detect/громкость + выборка кадров -> Gemini vision.
- moderate_video(video: VideoItem) -> None
  Объединяет текстовый и визуальный слой: is_approved=True только если
  оба вердикта положительны. Сохраняет rejection_reason, educational_score,
  topic_tags, transcript_summary и создаёт QuizQuestion из quizzes.
"""

from app.schemas.moderation import VideoModerationResultSchema, VisualModerationResultSchema


async def moderate_transcript(transcript: str, target_age: int) -> VideoModerationResultSchema:
    raise NotImplementedError("Текстовая модерация будет реализована на Этапе 2")


async def moderate_visual(video_local_path: str) -> VisualModerationResultSchema:
    raise NotImplementedError("Визуальный слой модерации будет реализован на Этапе 2")
