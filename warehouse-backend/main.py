from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo, database_health
from core.database.indexes import ensure_indexes
from core.exceptions import register_exception_handlers
from core.logger import configure_logging
from core.apis.routes import api_routers

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect MongoDB and create indexes for the application lifespan."""
    await connect_to_mongo()
    await ensure_indexes()
    logger.info("MongoDB connected")
    yield
    await close_mongo_connection()
    logger.info("MongoDB disconnected")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.state.logger = logger


@app.middleware("http")
async def request_logging(request, call_next):
    """Log every API request with method, path, status and elapsed time."""
    started = perf_counter()
    response = await call_next(request)
    logger.info("%s %s -> %s in %.1fms", request.method, request.url.path, response.status_code, (perf_counter() - started) * 1000)
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
for api_router in api_routers:
    app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str | dict[str, str]]:
    """Return process and database readiness for deployment checks."""
    return {"status": "healthy", "database": await database_health()}
