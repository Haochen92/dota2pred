import redis
from typing import Optional

class RedisClient:
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = redis.Redis(
                host='localhost',
                port=6379,
                decode_response=True
            )
        
        return cls._instance
    
    @classmethod
    def close_instance(cls):
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None