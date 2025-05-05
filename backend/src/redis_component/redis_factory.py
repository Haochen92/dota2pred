import redis.asyncio as redis
from typing import Dict

class RedisClientFactory:
    _instances: Dict[str, redis.Redis] = {}
    
    @classmethod
    def create_instance(cls, env: str = 'prod') -> redis.Redis:
        if env not in cls._instances or cls._instances[env] is None:
            port = 6390 if env == 'test' else 6380
            cls._instances[env] = redis.Redis(
                host='localhost',
                port=port,
                decode_responses=True
            )
        
        return cls._instances[env]
    
    @classmethod
    def close_instance(cls, env: str = 'prod'):
        if env in cls._instances and cls._instances[env] is not None:
            cls._instances[env].close()
            cls._instances[env] = None