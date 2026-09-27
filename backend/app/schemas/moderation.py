from typing import Literal

from pydantic import BaseModel, Field


class QuizOptionSchema(BaseModel):
    label: str = Field(description="Короткий текст или текстовое описание варианта")
    emoji: str = Field(description="Крупная понятная эмодзи-иллюстрация для кнопки")
    is_correct: bool = Field(description="Флаг правильного ответа")


class GeneratedQuizSchema(BaseModel):
    question_voice_text: str = Field(
        description="Текст вопроса, который будет озвучен ребенку голосом через TTS"
    )
    options: list[QuizOptionSchema] = Field(
        min_length=2,
        max_length=4,
        description="Варианты ответов (2 для возраста 2 года, 3-4 для возраста 5 лет)",
    )
    correct_option_index: int = Field(ge=0, le=3)


class VideoModerationResultSchema(BaseModel):
    is_approved: bool = Field(
        description="True только для строго спокойного, развивающего и полезного контента"
    )
    rejection_reason: str | None = Field(
        default=None, description="Причина отклонения, если is_approved = False"
    )
    educational_score: int = Field(ge=1, le=10, description="Оценка обучающей ценности ролика")
    target_age: Literal[2, 5] = Field(description="Целевой возраст ребенка")
    topics: list[str] = Field(description="Ключевые темы и навыки, затрагиваемые в видео")
    summary: str = Field(description="Краткий сжатый пересказ сюжета ролика")
    quizzes: list[GeneratedQuizSchema] = Field(
        description="Сгенерированные интерактивные вопросы по содержанию"
    )


class VisualModerationResultSchema(BaseModel):
    """Второй слой модерации — анализ визуального ряда, а не только субтитров.

    Субтитров часто недостаточно: агрессивный монтаж, крики или мигающие
    эффекты могут присутствовать в ролике без соответствующего текста.
    Этот слой обрабатывает выборку кадров (через ffmpeg + Gemini vision)
    отдельно от текстовой модерации в VideoModerationResultSchema.
    """

    has_rapid_cuts: bool = Field(description="Клиповый монтаж быстрее ~1.5 сек на кадр")
    has_loud_or_jarring_audio: bool = Field(description="Резкие вскрики/визги/агрессивные звуки")
    has_flashing_effects: bool = Field(description="Мигающие/стробоскопические визуальные эффекты")
    is_visually_safe: bool = Field(description="Итоговый вердикт визуального слоя модерации")
    notes: str | None = Field(default=None, description="Пояснение вердикта")
