from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.database import PlatformEnum


class ChildProfileCreate(BaseModel):
    name: str
    age: int
    daily_limit_minutes: int = 30
    avatar_url: str | None = None


class ChildProfileUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    daily_limit_minutes: int | None = None
    avatar_url: str | None = None


class ChildProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    daily_limit_minutes: int
    avatar_url: str | None
    created_at: datetime


class ChannelSourceCreate(BaseModel):
    platform: PlatformEnum
    external_id: str
    channel_name: str | None = None
    target_age_group: int | None = None
    added_by: str | None = None


class ChannelSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: PlatformEnum
    external_id: str
    channel_name: str | None
    target_age_group: int | None
    is_active: bool
    added_by: str | None
    created_at: datetime


class CurrentTopicOut(BaseModel):
    month: int
    week: int
    topic: str
    status: str


class DailyStatOut(BaseModel):
    stat_date: date
    watched_minutes: float
    quiz_accuracy: float | None


class ChildStatsOut(BaseModel):
    child_id: int
    daily_limit_minutes: int
    today_watched_minutes: float
    today_remaining_minutes: float
    week_watched_minutes: float
    week_quiz_accuracy: float | None
    current_topic: CurrentTopicOut | None
    daily_breakdown: list[DailyStatOut]


class WatchHistoryItemOut(BaseModel):
    id: int
    video_id: int
    video_title: str
    watched_seconds: int
    completed: bool
    skipped: bool
    quiz_passed: bool
    attempts_count: int
    timestamp: datetime


class VideoSummaryOut(BaseModel):
    id: int
    title: str
    source_platform: PlatformEnum
    age_group: int
    is_approved: bool
    rejection_reason: str | None
    educational_score: int
    topic_tags: list[str]
    duration_sec: int
    channel_name: str | None


class VideoModerationPatch(BaseModel):
    is_approved: bool
    rejection_reason: str | None = None


class SystemStatusOut(BaseModel):
    gemini_configured: bool
    telegram_configured: bool
    children_count: int
    active_channels_count: int
    channels_count: int
    videos_total_count: int
    videos_approved_count: int
    videos_rejected_count: int


class IngestRunOut(BaseModel):
    status: str
    channels_count: int


class RetryModerationOut(BaseModel):
    status: str
    video_id: int
