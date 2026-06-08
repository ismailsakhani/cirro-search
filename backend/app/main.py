from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import feedback, health, search

app = FastAPI(title="cirro-search", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(feedback.router)
