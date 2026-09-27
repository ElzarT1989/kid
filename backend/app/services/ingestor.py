"""Контент-парсер (Этап 2).

Отвечает за фоновый обход белого списка каналов (ChannelSource) через
yt-dlp: получение свежих видео, извлечение субтитров/метаданных и —
в отличие от исходной PDF-спеки — локальное скачивание одобренных роликов
в VIDEO_STORAGE_PATH (VideoItem.local_video_path), а не кэширование
"живых" HLS/MP4 ссылок, которые протухают за часы, тогда как между
модерацией и показом по плану может пройти недели.

TODO (Этап 2):
- fetch_channel_videos(channel: ChannelSource) -> list[dict]
  Запрос свежих видео канала через yt-dlp (--flat-playlist для списка,
  затем точечная выгрузка метаданных + субтитров на каждое).
- extract_transcript(video_external_id: str) -> str | None
  Извлечение .vtt/.srt субтитров через yt-dlp.
- download_approved_video(video: VideoItem) -> str
  Скачивание одобренного (is_approved=True) видео в VIDEO_STORAGE_PATH,
  возврат локального пути для VideoItem.local_video_path.
- run_ingestion_cycle() -> None
  Точка входа для APScheduler (каждые INGESTOR_INTERVAL_HOURS часов):
  обходит все активные ChannelSource, создаёт новые VideoItem,
  передаёт их в moderator.moderate_video().
"""


async def run_ingestion_cycle() -> None:
    raise NotImplementedError("Ingestor будет реализован на Этапе 2")
