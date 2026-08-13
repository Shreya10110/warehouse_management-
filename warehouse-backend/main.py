from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo
from core.exceptions import register_exception_handlers
from core.logger import configure_logging
from cruds.user_crud import ensure_user_indexes
from routes.auth_routes import router as auth_router

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await ensure_user_indexes()
    logger.info("MongoDB connected")
    yield
    await close_mongo_connection()
    logger.info("MongoDB disconnected")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.state.logger = logger
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(auth_router, prefix=settings.api_prefix)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "database": "connected"}
