import json

from typing import List

from fastapi import APIRouter

from services.products import BillzService
from utils.cache import Cache


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

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

    if not search:
        data = await cache.redis_client.lrange("products", start, end-1)
        products = [json.loads(item) for item in data]
        exists = await cache.exists("products")

        if not exists:
            products = await BillzService().get_products()
            await cache.set("count", len(products))
            for item in products:
                await cache.redis_client.rpush("products", json.dumps(item))
            await cache.redis_client.expire("products", 300)
            products = products[start:end]

        count = await cache.get("count")
        result["count"] = int(count)

    else:
        data = await cache.redis_client.lrange("products", 0, -1)
        all_products = [json.loads(item) for item in data]
        exists = await cache.exists("products")

        if not exists:
            products = await BillzService().get_products()
            await cache.set("count", len(products))
            for item in products:
                await cache.redis_client.rpush("products", json.dumps(item))
            await cache.redis_client.expire("products", 300)

        products = [item for item in all_products if search.lower() in item["name"].lower()]
        result["count"] = len(products)
        products = products[start:end]

    result["products"] = products

    return result


@router.get("/categories")
async def get_categories():
    cache = Cache()
    cached = await cache.get("categories")

    if cached:
        return {"categories": json.loads(cached)}

    categories = await BillzService().get_categories()
    await cache.set("categories", json.dumps(categories), ex=300)
    return {"categories": categories}


@router.post("/by-category")
async def get_products_by_category(
    category_ids: List[str],
    limit: int = 10,
    page: int = 1,
):
    start = (page - 1) * limit
    end = start + limit

    cache = Cache()
    result = {}

    data = await cache.redis_client.lrange("products", 0, -1)
    all_products = [json.loads(item) for item in data]
    exists = await cache.exists("products")

    if not exists:
        all_products = await BillzService().get_products()
        await cache.set("count", len(all_products))
        for item in all_products:
            await cache.redis_client.rpush("products", json.dumps(item))
        await cache.redis_client.expire("products", 300)

    category_ids_set = {str(category_id) for category_id in category_ids}
    products = [
        item
        for item in all_products
        if str(item.get("category_id", "")) in category_ids_set
    ]
    result["count"] = len(products)
    result["products"] = products[start:end]

    return result
