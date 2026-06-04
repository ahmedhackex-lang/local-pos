"""
FastAPI application entry point
Initializes all components and starts server
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime

# Local imports
from config import settings
from database import init_db, Base, engine
from auth import create_default_users
from printer import init_printer_from_settings
from sync_service import start_sync_service
from database import SessionLocal

# API routers
from api import (
    auth_router,
    products_router,
    sales_router,
    inventory_router,
    reports_router,
    sync_router,
    users_router,
    system_router
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events
    """
    # STARTUP
    logger.info("=" * 60)
    logger.info("GROCERY POS SYSTEM - STARTING UP")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Create default users
    logger.info("Creating default users...")
    db = SessionLocal()
    create_default_users(db)
    db.close()
    
    # Initialize printer
    logger.info("Initializing printer...")
    init_printer_from_settings()
    
    # Start sync service
    logger.info("Starting sync service...")
    await start_sync_service()
    
    logger.info("=" * 60)
    logger.info("APPLICATION READY")
    logger.info(f"Server: http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)
    
    yield
    
    # SHUTDOWN
    logger.info("=" * 60)
    logger.info("GROCERY POS SYSTEM - SHUTTING DOWN")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Offline-First Point of Sale System for Pakistani Retail",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)


# CORS middleware (disabled for production - same-origin only)
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Jinja2 templates
templates = Jinja2Templates(directory="templates")


# Template context processor (add global variables)
@app.middleware("http")
async def add_template_globals(request: Request, call_next):
    """Add global variables to template context"""
    request.state.settings = settings
    request.state.now = datetime.now()
    response = await call_next(request)
    return response


# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(sales_router, prefix="/api/sales", tags=["Sales"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(sync_router, prefix="/api/sync", tags=["Sync"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(system_router, prefix="/api/system", tags=["System"])


# ===== FRONTEND ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login page"""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/cashier", response_class=HTMLResponse)
async def cashier_page(request: Request):
    """Cashier interface (requires authentication - handled by frontend)"""
    return templates.TemplateResponse("cashier.html", {"request": request})


@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    """Inventory management page"""
    return templates.TemplateResponse("inventory.html", {"request": request})


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports dashboard page"""
    return templates.TemplateResponse("reports.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """User management page"""
    return templates.TemplateResponse("users.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """System settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})


# ===== ERROR HANDLERS =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page"""
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "error": "Page not found"
        },
        status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page"""
    logger.error(f"Server error: {exc}")
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "error": "Internal server error"
        },
        status_code=500
    )


# ===== MAIN ENTRY POINT =====

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )