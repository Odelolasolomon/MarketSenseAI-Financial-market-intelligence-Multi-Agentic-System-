"""
FastAPI Application Setup
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from src.config.settings import get_settings
from src.utilities.logger import get_logger, setup_logging
from src.error_trace.exceptions import MultiAssetAIException

logger = get_logger(__name__)
settings = get_settings()

# Initialize logging
setup_logging()


# Response models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Multi-Asset AI",
        description="Multi-agent AI system for Forex & Crypto market analysis",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom exception handlers
    @app.exception_handler(MultiAssetAIException)
    async def custom_exception_handler(request: Request, exc: MultiAssetAIException):
        """Handle custom exceptions"""
        logger.error(f"Custom exception: {exc.message}")
        return JSONResponse(status_code=400, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors"""
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTPException", "message": exc.detail},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
            },
        )

    # Startup event - non-blocking for Cloud Run compatibility
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup (non-blocking)"""
        logger.info("Starting Multi-Asset AI API...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")

        # Initialize database (non-blocking)
        try:
            from src.infrastructure.database import get_db
            # Import ORM mappings to enforce table registration with metadata
            from src.infrastructure.orm import start_mappers
            start_mappers()
            
            db = get_db()
            db.create_tables()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization deferred: {str(e)}")

        # Test cache connection (non-blocking)
        try:
            from src.infrastructure.cache import get_cache

            cache = get_cache()
            if cache.health_check():
                logger.info("Cache connection established")
        except Exception as e:
            logger.warning(f"Cache initialization deferred: {str(e)}")

        # Cache initialization (kept separate)

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Shutting down Multi-Asset AI API...")

    # Root health endpoint for Cloud Run health checks
    @app.get("/", response_model=HealthResponse)
    async def root_health():
        """Root health check - Cloud Run calls this endpoint"""
        return HealthResponse(status="healthy", service="MarketSenseAI")
    
    # Include routers
    from src.adapters.web.api_routes import router
    from src.adapters.web.routes.langchain_memory_routes import (
        router as langchain_memory_router,
    )

    app.include_router(router, prefix="/api/v1")
    app.include_router(langchain_memory_router)

    return app


# Create app instance lazily to avoid import-time errors
try:
    app = create_app()
except Exception as e:
    logger.error(f"Failed to create app: {str(e)}", exc_info=True)
    # Create a minimal app for health checks
    app = FastAPI(title="Multi-Asset AI", version="0.1.0")
    
    class HealthResponse(BaseModel):
        status: str
        service: str
    
    @app.get("/", response_model=HealthResponse)
    async def fallback_health():
        return HealthResponse(status="error", service="MarketSenseAI")
