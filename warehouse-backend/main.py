from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo
from core.exceptions import register_exception_handlers
from core.logger import configure_logging
from core.indexes import ensure_indexes
from routes.audit_routes import router as audit_router
from routes.approval_routes import router as approval_router
from routes.auth_routes import router as auth_router
from routes.dashboard_routes import router as dashboard_router
from routes.inbound_routes import router as inbound_router
from routes.inventory_routes import router as inventory_router
from routes.issue_routes import router as issue_router
from routes.master_routes import router as master_router
from routes.order_routes import router as order_router

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
for api_router in (auth_router, approval_router, master_router, inventory_router, inbound_router, order_router, issue_router, audit_router, dashboard_router):
    app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Return process and database readiness for deployment checks."""
    return {"status": "healthy", "database": "connected"}
