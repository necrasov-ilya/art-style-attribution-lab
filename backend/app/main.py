"""FastAPI main application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.database import engine, Base

# Import all models to ensure they're registered with Base
from app.models import User, AnalysisHistory, CollaborativeSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered art style attribution and analysis service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Alternative
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for serving images
app.mount("/api/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Include API router
app.include_router(api_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
