import logging

import aiohttp
from aiohttp import ClientResponse

from utils.cache import Cache

import os
from dotenv import load_dotenv
load_dotenv()

BILLZ_SECRET_KEY = os.getenv("BILLZ_SECRET_KEY")

logger = logging.getLogger(__name__)

class Client:
    def __init__(self):
        self.cache = Cache()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        access_key = await self.get_access_token()
        self.session.headers.update({"Authorization": f"Bearer {access_key}"})
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
        self.session = None

    async def update_access_token(self, access_token):
        await self.cache.set("ACCESS_TOKEN", access_token)
    
    async def get_access_token(self):
        access_token = await self.cache.get("ACCESS_TOKEN")
        if not access_token:
            await self.login()
            return await self.get_access_token()
        return access_token.decode()
    
    async def login(self):
        url = 'https://api-admin.billz.ai/v1/auth/login'
        payload = {"secret_token": BILLZ_SECRET_KEY}

        async with self.session.post(url, json=payload) as response:
            print(response)
            data = await response.json()
            print(data)
            access_token = data.get('data').get('access_token')
            await self.update_access_token(access_token)
            self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    async def post(self, url: str, payload: dict) -> ClientResponse:
        async with self.session.post(url, json=payload) as response:
            if response.status == 401:
                await self.login()
                return await self.post(url, payload)

            if response.status >= 400:
                body = await response.text()
                logger.error(
                    "Billz POST %s -> %s: %s", url, response.status, body[:500]
                )

            return await response.json()

    async def get(self, url: str) -> ClientResponse:
        async with self.session.get(url) as response:
            if response.status == 401:
                await self.login()
                return await self.get(url)

            if response.status >= 400:
                body = await response.text()
                logger.error(
                    "Billz GET %s -> %s: %s", url, response.status, body[:500]
                )

            return await response.json()

