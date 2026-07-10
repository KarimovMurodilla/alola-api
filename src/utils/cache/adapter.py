""" This file contains the cache adapter """
from typing import Any, List, Optional, TypeVar, overload, final

from redis.asyncio.client import Redis

import config as conf


def build_redis_client() -> Redis:
    """Build redis client"""
    return Redis(
        host=conf.host,
        db=conf.db,
        port=conf.port,
        password=conf.passwd,
        username=conf.username,
    )


class Cache:
    """Cache adapter"""

    def __init__(self, redis: Optional[Redis] = None):
        self.client = redis or build_redis_client()

    @property
    def redis_client(self) -> Redis:
        """
        Redis client which used in the cache adapter
        :return:
        """
        return self.client

    @final
    async def get(self, key: str) -> bytes:
        """
        Get a value from cache database
        :param key:
        :return: Value
        """
        return await self.client.get(str(key))

    @final
    async def set(self, key: str, value: Any, ex: float = None):
        """
        Set a value to cache database
        :param key: Key to set
        :param value: Value in a serializable type
        :return: Nothing
        """
        await self.client.set(name=str(key), value=value, ex=ex)  # noqa

    @overload
    async def exists(self, key: str):
        """
        Check whether key has already defined or not
        :param key:
        :return: (bool) Result
        """
        ...

    @overload
    async def exists(self, *keys: List[str]):
        """
        Overload of method to check many keys
        :param keys:
        :return:
        """
        ...

    async def exists(self, keys: str | List[str]):
        if not isinstance(keys, list):
            return await self.client.exists(str(keys))
        else:
            return await self.client.exists(*map(str, keys))