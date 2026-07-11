import json
import logging

from typing import List

from fastapi import APIRouter, HTTPException
from redis.exceptions import RedisError

from services.products import BillzService
from utils.cache import Cache


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


async def _populate_cache(cache: Cache, products: list) -> None:
    """Best-effort cache population. Never lets a Redis failure bubble up."""
    try:
        await cache.set("count", len(products))
        pipe = cache.redis_client.pipeline()
        pipe.delete("products")
        for item in products:
            pipe.rpush("products", json.dumps(item))
        pipe.expire("products", 300)
        await pipe.execute()
    except RedisError as exc:
        logger.warning("Failed to populate products cache, serving uncached: %s", exc)


@router.get("")
async def get_products(
    limit: int,
    page: int,
    search: str = None,
):
    start = (page - 1) * limit
    end = start + limit

    cache = Cache()
    result = {}

    # Try to serve from cache; any Redis failure falls back to Billz directly.
    all_products = None
    try:
        exists = await cache.exists("products")
        if not exists:
            all_products = await BillzService().get_products()
            await _populate_cache(cache, all_products)

        if search and all_products is None:
            data = await cache.redis_client.lrange("products", 0, -1)
            all_products = [json.loads(item) for item in data]
        elif not search and all_products is None:
            data = await cache.redis_client.lrange("products", start, end - 1)
            products = [json.loads(item) for item in data]
            count = await cache.get("count")
            result["count"] = int(count) if count is not None else 0
    except RedisError as exc:
        logger.warning("Redis unavailable, serving products directly from Billz: %s", exc)
        all_products = await BillzService().get_products()

    if search:
        products = [
            item for item in all_products
            if search.lower() in item["name"].lower()
        ]
        result["count"] = len(products)
        products = products[start:end]
    elif all_products is not None:
        # Cache miss/unavailable path: we hold the full list in memory.
        result["count"] = len(all_products)
        products = all_products[start:end]

    result["products"] = products

    return result


@router.get("/categories")
async def get_categories():
    cache = Cache()
    try:
        cached = await cache.get("categories")
        if cached:
            return {"categories": json.loads(cached)}
    except RedisError as exc:
        logger.warning("Redis unavailable reading categories: %s", exc)

    categories = await BillzService().get_categories()
    try:
        await cache.set("categories", json.dumps(categories), ex=300)
    except RedisError as exc:
        logger.warning("Failed to cache categories: %s", exc)
    return {"categories": categories}


@router.post("/by-category")
async def get_products_by_category(
    category_ids: List[str],
    limit: int = 10,
    page: int = 1,
):
    return await BillzService().get_products_by_category(category_ids, limit, page)


@router.get("/{product_id}")
async def get_product_detail(product_id: str):
    """Return the full grouped product for a given Billz product id.

    Serves from the Redis 'products' cache when warm; on a cache miss/cold
    cache it fetches fresh from Billz, repopulates the cache best-effort and
    then resolves the product.
    """
    cache = Cache()

    # Try the cache first; any Redis failure falls back to Billz directly.
    try:
        if await cache.exists("products"):
            data = await cache.redis_client.lrange("products", 0, -1)
            for item in data:
                product = json.loads(item)
                if BillzService._product_matches_id(product, product_id):
                    return product
    except RedisError as exc:
        logger.warning("Redis unavailable reading product detail: %s", exc)

    # Cache cold, unavailable, or product not present: fetch fresh from Billz.
    all_products = await BillzService().get_products()
    await _populate_cache(cache, all_products)

    for product in all_products:
        if BillzService._product_matches_id(product, product_id):
            return product

    raise HTTPException(status_code=404, detail="Product not found")
