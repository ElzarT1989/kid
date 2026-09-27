from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import ChannelSource, ChildProfile
from app.schemas.admin import (
    ChannelSourceCreate,
    ChannelSourceOut,
    ChildProfileCreate,
    ChildProfileOut,
    ChildProfileUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/children", response_model=ChildProfileOut)
async def create_child(payload: ChildProfileCreate, db: AsyncSession = Depends(get_db)) -> ChildProfile:
    child = ChildProfile(**payload.model_dump())
    db.add(child)
    await db.commit()
    await db.refresh(child)
    return child


@router.get("/children", response_model=list[ChildProfileOut])
async def list_children(db: AsyncSession = Depends(get_db)) -> list[ChildProfile]:
    result = await db.execute(select(ChildProfile))
    return list(result.scalars().all())


@router.get("/children/{child_id}", response_model=ChildProfileOut)
async def get_child(child_id: int, db: AsyncSession = Depends(get_db)) -> ChildProfile:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return child


@router.patch("/children/{child_id}", response_model=ChildProfileOut)
async def update_child(
    child_id: int, payload: ChildProfileUpdate, db: AsyncSession = Depends(get_db)
) -> ChildProfile:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(child, field, value)
    await db.commit()
    await db.refresh(child)
    return child


@router.delete("/children/{child_id}", status_code=204)
async def delete_child(child_id: int, db: AsyncSession = Depends(get_db)) -> None:
    child = await db.get(ChildProfile, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child profile not found")
    await db.delete(child)
    await db.commit()


@router.post("/channels", response_model=ChannelSourceOut)
async def create_channel(
    payload: ChannelSourceCreate, db: AsyncSession = Depends(get_db)
) -> ChannelSource:
    channel = ChannelSource(**payload.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.get("/channels", response_model=list[ChannelSourceOut])
async def list_channels(
    active_only: bool = True, db: AsyncSession = Depends(get_db)
) -> list[ChannelSource]:
    query = select(ChannelSource)
    if active_only:
        query = query.where(ChannelSource.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete("/channels/{channel_id}", status_code=204)
async def deactivate_channel(channel_id: int, db: AsyncSession = Depends(get_db)) -> None:
    channel = await db.get(ChannelSource, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = False
    await db.commit()
