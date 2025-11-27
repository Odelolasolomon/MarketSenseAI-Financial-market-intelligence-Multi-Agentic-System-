from functools import lru_cache
from src.config.settings import get_settings
from src.utilities.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Define CACHE_MARKET_DATA constant
CACHE_MARKET_DATA = "market_data"

class InMemoryCacheManager:
    """In-memory cache manager for fallback"""
    def __init__(self):
        self.cache = {}

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value: str, ttl: int = None):
        self.cache[key] = value

    def health_check(self):
        return True

if settings.redis_url.startswith("memory://"):
    # Use in-memory cache
    _cache_manager = InMemoryCacheManager()
else:
    import redis
    class RedisCacheManager:
        """Manages Redis cache operations"""
        def __init__(self, redis_url: str):
            self.client = redis.from_url(redis_url)
            self.client.ping()
            logger.info("Redis cache initialized")

        def get(self, key: str):
            return self.client.get(key)

        def set(self, key: str, value: str, ttl: int = 3600):
            self.client.setex(key, ttl, value)

        def health_check(self):
            return self.client.ping()

    _cache_manager = RedisCacheManager(settings.redis_url)

def get_cache():
    """Return the cache manager instance"""
    return _cache_manager