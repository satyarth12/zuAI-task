from contextlib import asynccontextmanager

import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from server import server_settings
from src.genai_process.routes import extraction_router
from src.sample_paper.routes import sample_paper_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = await Redis.from_url(
        f"redis://{server_settings.REDIS_HOST}:{server_settings.REDIS_PORT}",
        password=server_settings.REDIS_PASSWORD,
        encoding="utf-8",
        decode_responses=True,
    )
    await FastAPILimiter.init(redis_connection)
    yield
    await FastAPILimiter.close()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": f"Hello World from {server_settings.APP_NAME}"}


app.include_router(sample_paper_router)
app.include_router(extraction_router)

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=server_settings.HOST,
        port=server_settings.PORT,
        reload=server_settings.DEBUG_MODE,
    )
