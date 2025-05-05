import uvicorn
from redis import asyncio as aioredis

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
