from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.api.v1 import auth, articles

app = FastAPI(
    title="Smart News Aggregator API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add CORS middleware for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - replace with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    articles.router,
    prefix=f"{settings.API_V1_STR}/articles",
    tags=["Articles"]
)

@app.get("/", include_in_schema=False)
async def docs_redirect():
    """Redirects to API documentation."""
    return RedirectResponse(url="/docs")