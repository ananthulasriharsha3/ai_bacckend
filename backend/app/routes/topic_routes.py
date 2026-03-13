"""Topic-related API routes: create single, bulk, list topics."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_db_context
from app.schemas import BulkTopicsCreate, TopicCreate, TopicResponse
from app.services.topic_service import (
    create_topic_with_qa,
    create_topic_with_qa_from_name,
    get_all_topics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicResponse)
async def create_topic(
    payload: TopicCreate,
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """
    Create a topic, generate 8–10 Q&A via OpenAI, and store in DB.
    """
    try:
        topic = await create_topic_with_qa(db, payload)
        return TopicResponse.model_validate(topic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("", response_model=list[TopicResponse])
async def list_topics(db: AsyncSession = Depends(get_db)) -> list[TopicResponse]:
    """Return all topics."""
    topics = await get_all_topics(db)
    return [TopicResponse.model_validate(t) for t in topics]


@router.post("/bulk")
async def create_topics_bulk(
    payload: BulkTopicsCreate,
) -> dict:
    """
    Accept a list of topic names. For each topic: create in DB, generate Q&A via OpenAI,
    store questions. Uses background processing with rate-limited OpenAI calls.
    """
    topics = [t.strip() for t in payload.topics if t and t.strip()]
    if not topics:
        raise HTTPException(status_code=400, detail="No valid topics provided")

    async def process_bulk():
        async with get_db_context() as session:
            created: list[UUID] = []
            failed: list[tuple[str, str]] = []
            for topic_name in topics:
                try:
                    topic = await create_topic_with_qa_from_name(session, topic_name)
                    created.append(topic.id)
                    logger.info("Bulk: created topic id=%s name=%s", topic.id, topic_name)
                except Exception as e:
                    logger.exception("Bulk: failed for topic=%s", topic_name)
                    failed.append((topic_name, str(e)))
            if failed:
                logger.warning("Bulk completed with %d failures: %s", len(failed), failed)

    # Schedule background task on the same event loop (avoid asyncio.run / new loop issues)
    asyncio.create_task(process_bulk())

    return {
        "message": "Bulk topic creation started in background",
        "topic_count": len(topics),
        "topics": topics,
    }
