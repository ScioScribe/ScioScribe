"""
Main FastAPI application for ScioScribe backend.

This is the entry point for the ScioScribe backend API, including
experiment planning, data cleaning, analysis, and other AI agent functionality.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dataclean import router as dataclean_router
from api.planning import router as planning_router
from api.analysis import router as analysis_router
from api.database import router as database_router
# Import database initialization functions
from database import init_db, check_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ScioScribe API",
    description="AI-powered research co-pilot backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dataclean_router)
app.include_router(planning_router)
app.include_router(analysis_router)
app.include_router(database_router)

# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    logger.info("=== Starting ScioScribe API server ===")
    try:
        logger.info("Step 1: Checking database connection...")
        if check_db_connection():
            logger.info("✓ Database connection verified successfully")
        else:
            logger.warning("✗ Database connection failed - attempting to initialize...")

            logger.info("Step 2: Initializing database...")
            init_db()

            logger.info("Step 3: Re-checking connection after initialization...")
            if check_db_connection():
                logger.info("✓ Database initialized and connected successfully")
            else:
                logger.error("✗ Database initialization failed - server may not function properly")

        # Additional verification: Check if experiments table exists
        logger.info("Step 4: Verifying experiments table exists...")
        try:
            from database.database import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments';"))
                table_exists = result.fetchone() is not None
                if table_exists:
                    logger.info("✓ Experiments table exists in database")
                else:
                    logger.error("✗ Experiments table NOT found - forcing recreation...")
                    from database.models import Base
                    Base.metadata.create_all(bind=engine)
                    logger.info("✓ Tables recreated")
        except Exception as table_check_error:
            logger.error(f"✗ Table verification failed: {table_check_error}")
    except Exception as e:
        logger.error(f"Database startup error: {e}")
        logger.warning("Server starting without database - some features may not work")

    logger.info("=== ScioScribe API server startup complete ===")

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "ScioScribe API is running",
        "version": "1.0.0",
        "status": "healthy",
        "available_modules": [
            "experiment-planning-hitl",
            "data-cleaning",
            "analysis",
            "database"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 