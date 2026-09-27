import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PlatformEnum(str, enum.Enum):
    YOUTUBE = "youtube"
    VK = "vk"


class CurriculumStatusEnum(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


class PlaylistStatusEnum(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class ChildProfile(Base):
    __tablename__ = "child_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(Integer)  # 2 или 5
    daily_limit_minutes: Mapped[int] = mapped_column(Integer, default=30)
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    curriculum_nodes: Mapped[list["CurriculumNode"]] = relationship(back_populates="child")
    watch_logs: Mapped[list["WatchLog"]] = relationship(back_populates="child")
    daily_playlists: Mapped[list["DailyPlaylist"]] = relationship(back_populates="child")


class ChannelSource(Base):
    """Белый список одобренных каналов/плейлистов (Seed List).

    Управляется через Telegram-бота (/add_channel, /list_channels), а не
    статическим конфиг-файлом — родитель может расширять список без деплоя.
    """

    __tablename__ = "channel_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum))
    external_id: Mapped[str] = mapped_column(String(150), index=True)
    channel_name: Mapped[str | None] = mapped_column(String(255))
    target_age_group: Mapped[int | None] = mapped_column(Integer)  # 2, 5 или NULL = оба
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[str | None] = mapped_column(String(100))  # telegram username/id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    videos: Mapped[list["VideoItem"]] = relationship(back_populates="channel")

    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_channel_platform_external_id"),)


class CurriculumNode(Base):
    __tablename__ = "curriculum_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id"))
    month: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(100))
    target_skills: Mapped[dict] = mapped_column(JSON)  # ["colors", "counting"]
    status: Mapped[CurriculumStatusEnum] = mapped_column(
        Enum(CurriculumStatusEnum), default=CurriculumStatusEnum.PLANNED
    )

    child: Mapped["ChildProfile"] = relationship(back_populates="curriculum_nodes")


class VideoItem(Base):
    __tablename__ = "video_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channel_sources.id"))
    source_platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum))
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    duration_sec: Mapped[int] = mapped_column(Integer)
    transcript_text: Mapped[str | None] = mapped_column(Text)
    transcript_summary: Mapped[str | None] = mapped_column(Text)
    age_group: Mapped[int] = mapped_column(Integer)  # 2 или 5
    topic_tags: Mapped[dict] = mapped_column(JSON)  # ["shapes", "animals"]
    educational_score: Mapped[int] = mapped_column(Integer)  # 1-10
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(255))

    # Локально скачанный файл одобренного видео, а не кэш "живой" HLS/MP4
    # ссылки — та протухает за часы, а между модерацией и показом по
    # плану может пройти недели.
    local_video_path: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["ChannelSource"] = relationship(back_populates="videos")
    quizzes: Mapped[list["QuizQuestion"]] = relationship(back_populates="video")
    playlist_items: Mapped[list["DailyPlaylistItem"]] = relationship(back_populates="video")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_items.id"))
    question_text: Mapped[str] = mapped_column(Text)
    audio_tts_path: Mapped[str | None] = mapped_column(String(255))
    options_json: Mapped[dict] = mapped_column(JSON)  # [{"label": "...", "emoji": "🐶", "is_correct": true}]
    correct_option_index: Mapped[int] = mapped_column(Integer)

    video: Mapped["VideoItem"] = relationship(back_populates="quizzes")


class DailyPlaylist(Base):
    """Персистентный дневной плейлист ребёнка.

    В отличие от исходной спеки (где план строился "на лету" из
    CurriculumNode), плейлист сохраняется как отдельная сущность — это
    даёт стабильный порядок показа при перезапуске плеера и историю того,
    что реально было запланировано на день.
    """

    __tablename__ = "daily_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id"))
    playlist_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[PlaylistStatusEnum] = mapped_column(
        Enum(PlaylistStatusEnum), default=PlaylistStatusEnum.PLANNED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["ChildProfile"] = relationship(back_populates="daily_playlists")
    items: Mapped[list["DailyPlaylistItem"]] = relationship(
        back_populates="playlist", order_by="DailyPlaylistItem.order_index"
    )

    __table_args__ = (UniqueConstraint("child_id", "playlist_date", name="uq_child_playlist_date"),)


class DailyPlaylistItem(Base):
    __tablename__ = "daily_playlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("daily_playlists.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("video_items.id"))
    order_index: Mapped[int] = mapped_column(Integer)

    playlist: Mapped["DailyPlaylist"] = relationship(back_populates="items")
    video: Mapped["VideoItem"] = relationship(back_populates="playlist_items")


class WatchLog(Base):
    __tablename__ = "watch_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("video_items.id"))
    watched_seconds: Mapped[int] = mapped_column(Integer)

    # Не только длительность просмотра — отдельно фиксируем, было ли видео
    # досмотрено полностью или пропущено ребёнком/родителем.
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)

    quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["ChildProfile"] = relationship(back_populates="watch_logs")
