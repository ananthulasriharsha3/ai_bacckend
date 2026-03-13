"""Topic and Q&A business logic with database and OpenAI integration."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question, Topic
from app.schemas import QuestionAnswerPair, TopicCreate, TopicResponse
from app.services.openai_service import generate_qa_for_topic

logger = logging.getLogger(__name__)


async def create_topic_with_qa(session: AsyncSession, payload: TopicCreate) -> Topic:
    """
    Create a topic, generate 8–10 Q&A via OpenAI, and persist topic + questions.
    """
    topic = Topic(topic_name=payload.topic_name)
    session.add(topic)
    await session.flush()

    try:
        qa_pairs = await generate_qa_for_topic(payload.topic_name)
    except Exception as e:
        logger.exception("Failed to generate Q&A for topic=%s", payload.topic_name)
        raise

    for pair in qa_pairs:
        session.add(
            Question(
                topic_id=topic.id,
                question=pair.question,
                answer=pair.answer,
            )
        )
    await session.flush()
    await session.refresh(topic)
    logger.info("Created topic id=%s with %d questions", topic.id, len(qa_pairs))
    return topic


async def get_all_topics(session: AsyncSession) -> list[Topic]:
    """Return all topics ordered by created_at."""
    result = await session.execute(select(Topic).order_by(Topic.created_at.desc()))
    return list(result.scalars().all())


async def get_topic_by_id(session: AsyncSession, topic_id: UUID) -> Topic | None:
    """Return a topic by id or None."""
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    return result.scalar_one_or_none()


async def get_questions_by_topic_id(
    session: AsyncSession, topic_id: UUID
) -> list[Question]:
    """Return all questions for a topic."""
    result = await session.execute(
        select(Question).where(Question.topic_id == topic_id).order_by(Question.created_at)
    )
    return list(result.scalars().all())


async def create_topic_with_qa_from_name(
    session: AsyncSession, topic_name: str
) -> Topic:
    """Create a topic from a string name and generate Q&A (used by bulk)."""
    payload = TopicCreate(topic_name=topic_name.strip())
    return await create_topic_with_qa(session, payload)
