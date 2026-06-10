from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.products import BillzService


router = APIRouter(
    prefix="/billz",
    tags=["Billz Operations"],
)


class LoginSchema(BaseModel):
    secret_token: Optional[str] = None


class OrderCreateSchema(BaseModel):
    shop_id: str


class OrderProductSchema(BaseModel):
    product_id: str
    seller_ids: List[str]
    sold_measurement_value: float = 1
    used_wholesale_price: bool = True
    is_manual: bool = False


class PaymentTypeSchema(BaseModel):
    name: str


class PaymentSchema(BaseModel):
    company_payment_type_id: str
    paid_amount: float
    company_payment_type: Optional[PaymentTypeSchema] = None
    returned_amount: float = 0


class OrderCompleteSchema(BaseModel):
    payments: List[PaymentSchema]
    comment: Optional[str] = None
    with_cashback: int = 0
    without_cashback: bool = False
    skip_ofd: bool = False


@router.post("/auth/login")
async def login(
    body: LoginSchema,
):
    return await BillzService().login(body.secret_token)


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


@router.post("/order-product/{order_id}")
async def add_order_product(
    order_id: str,
    body: OrderProductSchema,
):
    return await BillzService().add_order_product(
        order_id=order_id,
        product_id=body.product_id,
        seller_ids=body.seller_ids,
        sold_measurement_value=body.sold_measurement_value,
        used_wholesale_price=body.used_wholesale_price,
        is_manual=body.is_manual,
    )


@router.post("/order-payment/{order_id}")
async def complete_order(
    order_id: str,
    body: OrderCompleteSchema,
):
    return await BillzService().complete_order(
        order_id=order_id,
        payments=[p.model_dump() for p in body.payments],
        comment=body.comment,
        with_cashback=body.with_cashback,
        without_cashback=body.without_cashback,
        skip_ofd=body.skip_ofd,
    )


@router.get("/client")
async def get_client(
    chat_id: str,
):
    return await BillzService().get_client(chat_id)
