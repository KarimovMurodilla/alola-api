import time
import logging
import uvicorn
from redis import asyncio as aioredis

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from api.routers import all_routers
from config import FRONTEND_BASE_URL

app = FastAPI(
    title="CRUD Users"
)

for router in all_routers:
    if isinstance(router, dict):
        app.include_router(**router)

    else:
        app.include_router(router)

origins = [
    FRONTEND_BASE_URL,
    "http://localhost:3000"
]

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        str(request.url),
        response.status_code,
        duration,
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    redis =  aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

if __name__ == "__main__":
    uvicorn.run(app="main:app", reload=True)
