import redis.asyncio as redis
from typing import Dict, Optional


class RedisClientFactory:
    _instances: Dict[str, Optional[redis.Redis]] = {}

    @classmethod
    def create_instance(cls, env: str = "prod") -> redis.Redis:
        if env not in cls._instances or cls._instances[env] is None:
            port = 6390 if env == "test" else 6380
            cls._instances[env] = redis.Redis(host="localhost", port=port, decode_responses=True)

        instance = cls._instances[env]
        assert instance is not None
        return instance

    @classmethod
    async def close_instance(cls, env: str = "prod") -> None:
        if env in cls._instances and cls._instances[env] is not None:
            instance = cls._instances[env]
            if instance:
                await instance.aclose()
                cls._instances[env] = None
