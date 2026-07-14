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

# Redis list of pinned base names, newest pin first. No TTL: it is the owner's
# manual ordering, not a cache of Billz data.
PINNED_KEY = "pinned_products"


def _base_name(name: str) -> str:
    return name.split(" / ")[0].strip()


async def _get_pinned_names(cache: Cache) -> list:
    try:
        data = await cache.redis_client.lrange(PINNED_KEY, 0, -1)
        return [item.decode() for item in data]
    except RedisError as exc:
        logger.warning("Failed to read pinned products, keeping Billz order: %s", exc)
        return []


def _apply_pinned_order(products: list, pinned_names: list) -> list:
    """Move pinned products to the front, in pin order (newest pin first)."""
    if not pinned_names:
        return products
    order = {name: idx for idx, name in enumerate(pinned_names)}
    pinned = [item for item in products if _base_name(item["name"]) in order]
    rest = [item for item in products if _base_name(item["name"]) not in order]
    pinned.sort(key=lambda item: order[_base_name(item["name"])])
    return pinned + rest


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
            all_products = _apply_pinned_order(all_products, await _get_pinned_names(cache))
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


@router.get("/pinned")
async def get_pinned_products():
    return {"pinned": await _get_pinned_names(Cache())}


@router.post("/pin")
async def pin_product(name: str):
    """Pin a product to the top of the listing. The newest pin comes first."""
    base = _base_name(name)
    if not base:
        raise HTTPException(status_code=422, detail="Empty product name")

    cache = Cache()
    try:
        pipe = cache.redis_client.pipeline()
        pipe.lrem(PINNED_KEY, 0, base)
        pipe.lpush(PINNED_KEY, base)
        # Drop the cached listing so the new order applies on the next request.
        pipe.delete("products")
        await pipe.execute()
    except RedisError as exc:
        logger.warning("Failed to pin product %s: %s", base, exc)
        raise HTTPException(status_code=503, detail="Cache unavailable, try again later")

    logger.info("Product pinned to top: %s", base)
    return {"pinned": await _get_pinned_names(cache)}


@router.delete("/pin")
async def unpin_product(name: str):
    base = _base_name(name)
    cache = Cache()
    try:
        removed = await cache.redis_client.lrem(PINNED_KEY, 0, base)
        await cache.redis_client.delete("products")
    except RedisError as exc:
        logger.warning("Failed to unpin product %s: %s", base, exc)
        raise HTTPException(status_code=503, detail="Cache unavailable, try again later")

    if not removed:
        raise HTTPException(status_code=404, detail="Product is not pinned")
    logger.info("Product unpinned: %s", base)
    return {"pinned": await _get_pinned_names(cache)}


@router.get("/{product_id}")
async def get_product_detail(product_id: str):
    """Return the full grouped product (all variants) for a Billz product id.

    Fetched fresh from Billz: the general `/products` cache only holds a subset
    of the catalog, so it can't be used to resolve an arbitrary product id.
    """
    product = await BillzService().get_product_detail(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
