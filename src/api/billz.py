import json
import redis

from fastapi import APIRouter
from fastapi_cache.decorator import cache

from api.dependencies import UOWDep

from schemas.users import UserSchemaEdit
from services.products import BillzService
from utils.cache import Cache


router = APIRouter(
    prefix="/billz",
    tags=["Billz Operations"],
)

@router.post("/order/{order_id}")
async def get_products(
    order_id: str,
):
    order = await BillzService().get_order(order_id)
    return order
