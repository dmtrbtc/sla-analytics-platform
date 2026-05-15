"""SLA Analytics Platform - Main Application Entry"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import configure_observability, health_check
from app.core.security_middleware import configure_security

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up SLA Analytics Platform")
    from app.seeds import seed_admin_user, seed_sla_definitions
    seed_sla_definitions()
    seed_admin_user()
    yield
    logger.info("Shutting down SLA Analytics Platform")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

configure_security(app)
configure_observability(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return await health_check()
