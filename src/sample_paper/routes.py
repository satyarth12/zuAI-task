from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

from src.sample_paper.schema import SamplePaper
from src.sample_paper.views import (
    CreateSamplePaperView,
    DeleteSamplePaperView,
    GetSamplePaperView,
    UpdateSamplePaperView,
)
from src.shared_resource.cache import RedisCacheRepository, get_redis_cache
from src.shared_resource.db import AsyncMongoRepository, get_mongo_repo

sample_paper_router = APIRouter(tags=["sample-paper"], prefix="/sample-papers")

# Rate limit: 10 requests per minute
sample_paper_rate_limiter = RateLimiter(times=10, seconds=60)


@sample_paper_router.post("/", dependencies=[Depends(sample_paper_rate_limiter)])
async def create_sample_paper(
    paper: SamplePaper,
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
):
    view = CreateSamplePaperView(mongo_repo=mongo_repo, cache=cache)
    return await view.create_sample_paper(paper)


@sample_paper_router.get(
    "/{paper_id}", dependencies=[Depends(sample_paper_rate_limiter)]
)
async def get_sample_paper(
    paper_id: str,
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
):
    view = GetSamplePaperView(mongo_repo=mongo_repo, cache=cache)
    return await view.get_sample_paper(paper_id)


@sample_paper_router.put(
    "/{paper_id}", dependencies=[Depends(sample_paper_rate_limiter)]
)
async def update_sample_paper(
    paper_id: str,
    paper_update: dict,
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
):
    view = UpdateSamplePaperView(mongo_repo=mongo_repo, cache=cache)
    return await view.update_sample_paper(paper_id, paper_update)


@sample_paper_router.delete(
    "/{paper_id}", dependencies=[Depends(sample_paper_rate_limiter)]
)
async def delete_sample_paper(
    paper_id: str,
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
):
    view = DeleteSamplePaperView(mongo_repo=mongo_repo, cache=cache)
    return await view.delete_sample_paper(paper_id)
