from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from services.products import BillzService


router = APIRouter(
    prefix="/billz",
    tags=["Billz Operations"],
)


class OrderCreateSchema(BaseModel):
    shop_id: str


class OrderProductSchema(BaseModel):
    product_id: str
    seller_ids: List[str]
    sold_measurement_value: float = 1
    used_wholesale_price: bool = True
    is_manual: bool = False


@router.post("/order/{order_id}")
async def get_order(
    order_id: str,
):
    order = await BillzService().get_order(order_id)
    return order


@router.post("/orders")
async def create_order(
    body: OrderCreateSchema,
):
    return await BillzService().create_order(body.shop_id)


@router.post("/order-product")
async def add_order_product(
    body: OrderProductSchema,
):
    return await BillzService().add_order_product(
        product_id=body.product_id,
        seller_ids=body.seller_ids,
        sold_measurement_value=body.sold_measurement_value,
        used_wholesale_price=body.used_wholesale_price,
        is_manual=body.is_manual,
    )


@router.get("/client")
async def get_client(
    chat_id: str,
):
    return await BillzService().get_client(chat_id)
