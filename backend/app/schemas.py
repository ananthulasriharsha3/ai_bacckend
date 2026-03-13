"""Pydantic schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ----- Topic -----


class TopicCreate(BaseModel):
    """Request body for creating a single topic."""

    topic_name: str = Field(..., min_length=1, max_length=500)


class TopicResponse(BaseModel):
    """Topic in API responses."""

    id: UUID
    topic_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ----- Question / Q&A -----


class QuestionAnswerPair(BaseModel):
    """Single Q&A pair (from OpenAI or API response)."""

    question: str
    answer: str


class QuestionResponse(BaseModel):
    """Question record in API responses."""

    id: UUID
    topic_id: UUID
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TopicWithQAResponse(BaseModel):
    """Topic with its questions and answers."""

    topic: TopicResponse
    questions: list[QuestionResponse]


# ----- Bulk -----


class BulkTopicsCreate(BaseModel):
    """Request body for bulk topic creation."""

    topics: list[str] = Field(..., min_length=1, max_length=5000)
