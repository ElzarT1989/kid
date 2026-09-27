"""Генератор годового учебного плана и адаптивности (Этап 4).

Иерархия: Годовой план -> Модуль (месяц) -> Тема (неделя) ->
Дневной плейлист (1-3 видео), персистентно сохраняемый в DailyPlaylist/
DailyPlaylistItem (не пересчитываемый на лету при каждом запросе плеера).

Динамическая сложность по результатам квизов за неделю (WatchLog.quiz_passed):
- >=80% успеха -> повышение сложности темы либо переход на следующий модуль
  (CurriculumNode.status -> MASTERED, создание следующего узла ACTIVE).
- <=50% успеха -> подбор дублирующих/закрепляющих роликов по той же теме
  с другим визуальным рядом (CurriculumNode.status -> NEEDS_REVIEW).

TODO (Этап 4):
- generate_weekly_topic(child: ChildProfile) -> CurriculumNode
- calculate_weekly_success_rate(child_id: int, week: int) -> float
- adapt_difficulty(child: ChildProfile) -> None
- build_daily_playlist(child: ChildProfile, target_date: date) -> DailyPlaylist
  Собирает 1-3 VideoItem под текущий CurriculumNode.status == ACTIVE и
  сохраняет DailyPlaylist/DailyPlaylistItem для отдачи через
  app/api/player.py::get_today_playlist.
"""


async def build_daily_playlist(child_id: int) -> None:
    raise NotImplementedError("Curriculum engine будет реализован на Этапе 4")
