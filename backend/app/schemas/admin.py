from datetime import datetime

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
