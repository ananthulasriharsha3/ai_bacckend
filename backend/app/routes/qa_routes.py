"""Q&A retrieval routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import QuestionResponse, TopicWithQAResponse, TopicResponse
from app.services.topic_service import get_questions_by_topic_id, get_topic_by_id

router = APIRouter(tags=["qa"])


@router.get("/topics/{topic_id}/qa", response_model=TopicWithQAResponse)
async def get_topic_qa(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TopicWithQAResponse:
    """Return the topic and all its questions and answers."""
    topic = await get_topic_by_id(db, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    questions = await get_questions_by_topic_id(db, topic_id)
    return TopicWithQAResponse(
        topic=TopicResponse.model_validate(topic),
        questions=[QuestionResponse.model_validate(q) for q in questions],
    )
