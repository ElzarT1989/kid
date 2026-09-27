"""Синтез речи для квиз-вопросов через edge-tts (Этап 2).

Заранее (при одобрении видео и генерации QuizQuestion) синтезирует .mp3
файл вопроса через edge-tts и сохраняет его в TTS_CACHE_PATH; путь пишется
в QuizQuestion.audio_tts_path. Плеер проигрывает готовый файл при открытии
QuizOverlay — без синтеза "на лету" во время просмотра ребёнком.

TODO (Этап 2):
- synthesize_question_audio(question_text: str, quiz_id: int) -> str
  edge-tts (голос ru-RU, например ru-RU-SvetlanaNeural) -> .mp3 в
  TTS_CACHE_PATH, возврат сохранённого пути.
"""


async def synthesize_question_audio(question_text: str, quiz_id: int) -> str:
    raise NotImplementedError("TTS-синтез будет реализован на Этапе 2")
