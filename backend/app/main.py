"""FastAPI application entrypoint with structured logging and error handling."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routes import qa_routes, topic_routes

# ----- Structured logging -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup; cleanup on shutdown. App still starts if DB is unreachable."""
    logger.info("Starting up: creating database tables if not exist")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except OSError as e:
        logger.warning(
            "Could not connect to database at startup (check DATABASE_URL and network): %s. "
            "App will start; DB endpoints will fail until connection works.",
            e,
        )
    except Exception as e:
        logger.warning(
            "Database startup failed: %s. App will start; fix DATABASE_URL and restart.",
            e,
        )
    yield
    logger.info("Shutting down")
    await engine.dispose()


app = FastAPI(
    title="Topics Q&A API",
    description="Generate and store topic Q&A using OpenAI and Supabase",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow local dev and deployed frontends to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-frontend-silk.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topic_routes.router)
app.include_router(qa_routes.router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
    )


@app.get("/health")
async def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}
