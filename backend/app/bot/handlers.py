from datetime import date, datetime, time

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from app.database import async_session_maker
from app.models.database import ChannelSource, ChildProfile, PlatformEnum, VideoItem, WatchLog

router = Router()


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    today_start = datetime.combine(date.today(), time.min)

    async with async_session_maker() as db:
        children_result = await db.execute(select(ChildProfile))
        children = list(children_result.scalars().all())

        if not children:
            await message.answer("Пока не создано ни одного детского профиля.")
            return

        lines = ["📊 <b>Статус на сегодня</b>"]
        for child in children:
            watched_result = await db.execute(
                select(func.coalesce(func.sum(WatchLog.watched_seconds), 0)).where(
                    WatchLog.child_id == child.id, WatchLog.timestamp >= today_start
                )
            )
            watched_seconds = watched_result.scalar_one()
            watched_minutes = round(watched_seconds / 60, 1)
            lines.append(
                f"• <b>{child.name}</b> ({child.age} лет): "
                f"{watched_minutes} / {child.daily_limit_minutes} мин"
            )

        await message.answer("\n".join(lines))


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(
            "Использование: /add_channel &lt;youtube|vk&gt; &lt;id_канала&gt; [возраст] [название]"
        )
        return

    parts = command.args.split(maxsplit=3)
    if len(parts) < 2:
        await message.answer(
            "Использование: /add_channel &lt;youtube|vk&gt; &lt;id_канала&gt; [возраст] [название]"
        )
        return

    platform_raw, external_id, *rest = parts
    try:
        platform = PlatformEnum(platform_raw.lower())
    except ValueError:
        await message.answer("Платформа должна быть 'youtube' или 'vk'.")
        return

    target_age: int | None = None
    channel_name: str | None = None
    if rest:
        if rest[0].isdigit():
            target_age = int(rest[0])
            channel_name = rest[1] if len(rest) > 1 else None
        else:
            channel_name = " ".join(rest)

    async with async_session_maker() as db:
        existing = await db.execute(
            select(ChannelSource).where(
                ChannelSource.platform == platform, ChannelSource.external_id == external_id
            )
        )
        if existing.scalars().first() is not None:
            await message.answer("Этот канал уже в белом списке.")
            return

        channel = ChannelSource(
            platform=platform,
            external_id=external_id,
            channel_name=channel_name,
            target_age_group=target_age,
            added_by=message.from_user.username if message.from_user else None,
        )
        db.add(channel)
        await db.commit()

    await message.answer(f"✅ Канал добавлен в белый список: {channel_name or external_id}")


@router.message(Command("list_channels"))
async def cmd_list_channels(message: Message) -> None:
    async with async_session_maker() as db:
        result = await db.execute(
            select(ChannelSource).where(ChannelSource.is_active.is_(True))
        )
        channels = list(result.scalars().all())

    if not channels:
        await message.answer("Белый список каналов пуст.")
        return

    lines = ["📺 <b>Одобренные каналы</b>"]
    for ch in channels:
        age_label = f", {ch.target_age_group} лет" if ch.target_age_group else ""
        lines.append(f"#{ch.id} [{ch.platform.value}] {ch.channel_name or ch.external_id}{age_label}")

    await message.answer("\n".join(lines))


@router.message(Command("block_video"))
async def cmd_block_video(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /block_video &lt;id&gt;")
        return

    video_id = int(command.args.strip())

    async with async_session_maker() as db:
        video = await db.get(VideoItem, video_id)
        if video is None:
            await message.answer(f"Видео #{video_id} не найдено.")
            return

        video.is_approved = False
        video.rejection_reason = "Заблокировано родителем через /block_video"
        await db.commit()

    await message.answer(f"🚫 Видео #{video_id} ({video.title}) исключено из базы.")


@router.message(Command("add_topic"))
async def cmd_add_topic(message: Message, command: CommandObject) -> None:
    await message.answer(
        "⏳ /add_topic пока не реализован — принудительное добавление тем "
        "в план недели появится вместе с curriculum engine (Этап 4)."
    )
