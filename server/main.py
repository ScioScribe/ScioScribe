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
from database import init_db  

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

@app.on_event("startup")
def startup_event():
    init_db()  # Initialize database tables on startup

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