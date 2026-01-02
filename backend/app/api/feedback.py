"""反馈 REST API"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.video_stream import VideoStream
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter()


async def _get_stream_or_404(db: AsyncSession, stream_id: str) -> VideoStream:
    result = await db.execute(
        select(VideoStream).where(VideoStream.id == stream_id)
    )
    stream = result.scalar_one_or_none()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    return stream


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="提交反馈",
)
async def create_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    await _get_stream_or_404(db, data.stream_id)

    feedback = Feedback(
        id=str(uuid.uuid4()),
        stream_id=data.stream_id,
        message=data.message,
        payload=data.payload or {},
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
