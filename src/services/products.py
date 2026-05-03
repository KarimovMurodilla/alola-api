from typing import Optional

from utils.custom_client import Client


class BillzService:
    def __init__(self):
        self.client = Client()

    @staticmethod
    def _prepare_products(products_data: list[dict]):
        products = {}

        if not products_data:
            return []

        for obj in products_data:
            if (
                obj.get('parent_id')
                and obj.get('main_image_url_full')
                and obj.get('product_supplier_stock')
                and obj['product_supplier_stock'][0].get('wholesale_price')
                and obj.get('shop_measurement_values')
                and obj['shop_measurement_values'][0].get('active_measurement_value')
                and obj.get('product_attributes')
            ):
                count = obj['shop_measurement_values'][0]['active_measurement_value']

                if products.get(obj['parent_id']):
                    product_attributes = obj['product_attributes'][0]
                    product_attributes['max_count'] = count
                    product_attributes['product_id'] = obj['id']
                    products[obj['parent_id']]['product_attributes'].append(product_attributes)
                else:
                    obj['product_attributes'][0]['max_count'] = count
                    obj['product_attributes'][0]['product_id'] = obj['id']
                    products[obj['parent_id']] = obj

        return list(products.values())

    @staticmethod
    def _prepare_products_by_category(products_data: list[dict]):
        products = {}

        if not products_data:
            return []

        for obj in products_data:
            shop_measurement_values = obj.get("shop_measurement_values") or []
            product_supplier_stock = obj.get("product_supplier_stock") or []
            product_attributes = obj.get("product_attributes") or []

            if not (
                obj.get("parent_id")
                and obj.get("main_image_url")
                and shop_measurement_values
                and product_supplier_stock
                and product_attributes
            ):
                continue

            count = shop_measurement_values[0].get("total_active_measurement_value")
            wholesale_price = product_supplier_stock[0].get("wholesale_price")
            if count is None or wholesale_price is None:
                continue

            if products.get(obj["parent_id"]):
                attribute = product_attributes[0]
                attribute["max_count"] = count
                attribute["product_id"] = obj["id"]
                products[obj["parent_id"]]["product_attributes"].append(attribute)
            else:
                obj["product_attributes"][0]["max_count"] = count
                obj["product_attributes"][0]["product_id"] = obj["id"]
                products[obj["parent_id"]] = obj

        return list(products.values())
    
    async def set_user(
        self,
        chat_id: str,
        first_name: str, 
        last_name: str, 
        phone_number: str, 
        date_of_birth: Optional[str] = '2022-05-14',
        gender: Optional[int] = 1,
    ):
        url = 'https://api-admin.billz.ai/v1/client'
        payload = {
            "chat_id": chat_id,
            "date_of_birth": date_of_birth,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "gender": gender
        }

        async with self.client as client:
            await client.post(url, payload)

    async def get_products(self):
        url = f'https://api-admin.billz.ai/v2/products?limit=4000&page=1' 
        
        async with self.client as client:
            data = await client.get(url)
            return self._prepare_products(data.get('products', []))


    async def get_categories(self):
        url = 'https://api-admin.billz.ai/v2/category'

        async with self.client as client:
            data = await client.get(url)
            return data.get('categories', [])

    async def get_products_by_category(self, category_ids: list[str], limit: int, page: int):
        url = 'https://api-admin.billz.ai/v2/product-search-with-filters'
        payload = {
            "category_ids": category_ids,
            "limit": limit,
            "page": page,
        }

        async with self.client as client:
            data = await client.post(url, payload)
            products = self._prepare_products_by_category(data.get('products', []))
            return {
                "count": data.get("count", len(products)),
                "products": products,
            }

    async def get_order(self, order_id: str):
        url = f"https://alola.billz.io/api/v2/order/{order_id}"
        
        async with self.client as client:
            data = await client.get(url)
            return data
