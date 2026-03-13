"""OpenAI API service for generating Q&A pairs with rate limiting."""

import asyncio
import json
import logging
import re
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas import QuestionAnswerPair

logger = logging.getLogger(__name__)

_settings = get_settings()
_client: Optional[AsyncOpenAI] = None
_semaphore: Optional[asyncio.Semaphore] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not _settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        _client = AsyncOpenAI(api_key=_settings.openai_api_key)
    return _client


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_settings.openai_max_concurrent)
    return _semaphore


async def generate_qa_for_topic(topic: str) -> list[QuestionAnswerPair]:
    """
    Call OpenAI Chat API to generate 8–10 Q&A pairs for the given topic.
    Uses a semaphore to limit concurrent requests.
    """
    sem = _get_semaphore()
    async with sem:
        return await _call_openai(topic)


async def _call_openai(topic: str) -> list[QuestionAnswerPair]:
    client = _get_client()
    # Use a fixed 10-question template for consistency across topics.
    prompt = (
        "You are creating standard interview-style Q&A.\n"
        f"Use EXACTLY the following 10 questions, replacing {{topic}} with \"{topic}\":\n\n"
        "1) What is {topic}?\n"
        "2) Why is {topic} important in modern technology?\n"
        "3) What are the key concepts of {topic}?\n"
        "4) What are the main advantages of {topic}?\n"
        "5) What are the limitations or challenges of {topic}?\n"
        "6) How is {topic} used in real-world applications?\n"
        "7) What tools or technologies are commonly used with {topic}?\n"
        "8) How does {topic} differ from related technologies?\n"
        "9) What are the best practices for implementing {topic}?\n"
        "10) What is the future scope of {topic}?\n\n"
        "For each of these 10 questions, generate a concise but clear answer.\n"
        "Return ONLY a valid JSON array with no other text. Each element must be an object\n"
        "with exactly two keys: \"question\" and \"answer\". Example format:\n"
        "[{\"question\": \"...\", \"answer\": \"...\"}]\n"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical interviewer. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
    except Exception as e:
        logger.exception("OpenAI API request failed for topic=%s", topic)
        raise RuntimeError(f"OpenAI API failed: {e}") from e

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError("OpenAI returned empty content")

    return _parse_qa_json(content.strip(), topic)


def _parse_qa_json(content: str, topic: str) -> list[QuestionAnswerPair]:
    """Parse JSON from model output; handle markdown code blocks if present."""
    text = content.strip()
    # Remove optional markdown code block
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("OpenAI response was not valid JSON for topic=%s: %s", topic, e)
        raise ValueError(f"Invalid JSON from OpenAI: {e}") from e

    if not isinstance(data, list):
        raise ValueError("OpenAI response is not a JSON array")

    result: list[QuestionAnswerPair] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        q = item.get("question")
        a = item.get("answer")
        if isinstance(q, str) and isinstance(a, str) and q.strip() and a.strip():
            result.append(QuestionAnswerPair(question=q.strip(), answer=a.strip()))

    if len(result) < 8:
        logger.warning(
            "OpenAI returned %d Q&A pairs for topic=%s (expected 8–10)",
            len(result),
            topic,
        )
    return result
