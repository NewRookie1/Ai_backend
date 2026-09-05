from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from .core.config import settings
from .core.database import engine, Base
from .routers import auth, speech, translation, image, products, orders, voice, market

logger = logging.getLogger("artisan_ai")

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Driven Market Linkage & Smart Cataloging API for Artisans",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(speech.router)
app.include_router(translation.router)
app.include_router(image.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(voice.router)
app.include_router(market.router)

@app.on_event("startup")
async def startup():
    # Never let a DB outage kill the whole service: /health and the
    # AI-only routes must stay up so the platform (Render) sees a live app.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")
    except Exception as exc:
        logger.warning("Database unavailable at startup, continuing: %s", exc)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
