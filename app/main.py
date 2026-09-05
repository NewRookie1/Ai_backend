from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import engine, Base
from .routers import auth, speech, translation, image, products, orders, voice, market

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
    Base.metadata.create_all(bind=engine)

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
