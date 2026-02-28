"""
Redis Caching Manager for Pattern Vector Verdict Engine
판정 결과 및 언어 정보 캐싱
"""

import json
import hashlib
import time
from typing import Any, Dict, Optional, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheConfig:
    """캐시 설정"""
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 3600,  # 1시간
        verdict_ttl: int = 1800,  # 30분
        language_ttl: int = 86400,  # 24시간
        enable_compression: bool = True
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.default_ttl = default_ttl
        self.verdict_ttl = verdict_ttl
        self.language_ttl = language_ttl
        self.enable_compression = enable_compression


class RedisCache:
    """Redis 기반 캐시 매니저"""

    def __init__(self, config: Optional[CacheConfig] = None):
        """초기화"""
        self.config = config or CacheConfig()
        self.client = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
        }

    def connect(self):
        """Redis 연결"""
        try:
            import redis
            self.client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # 연결 테스트
            self.client.ping()
            logger.info(f"Redis connected: {self.config.redis_host}:{self.config.redis_port}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            logger.info("Falling back to in-memory cache")
            self.client = None
            self._memory_cache = {}
            return False

    def _generate_key(self, prefix: str, data: Any) -> str:
        """캐시 키 생성"""
        # 데이터를 정렬된 JSON으로 변환하여 일관된 해시 생성
        data_str = json.dumps(data, sort_keys=True, default=str)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{data_hash}"

    def _get_ttl(self, cache_type: str) -> int:
        """캐시 타입별 TTL 반환"""
        ttl_map = {
            "verdict": self.config.verdict_ttl,
            "language": self.config.language_ttl,
            "comparison": self.config.verdict_ttl,
            "trace": self.config.verdict_ttl,
            "stats": 300,  # 5분
            "default": self.config.default_ttl,
        }
        return ttl_map.get(cache_type, self.config.default_ttl)

    def set(self, key: str, value: Any, ttl: Optional[int] = None, cache_type: str = "default") -> bool:
        """값 저장"""
        try:
            self.stats["total_requests"] += 1
            if ttl is None:
                ttl = self._get_ttl(cache_type)

            value_json = json.dumps(value, default=str)

            if self.client:
                self.client.setex(key, ttl, value_json)
            else:
                # In-memory fallback
                self._memory_cache[key] = {
                    "value": value_json,
                    "expires_at": time.time() + ttl
                }

            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats["errors"] += 1
            return False

    def get(self, key: str) -> Optional[Any]:
        """값 조회"""
        try:
            self.stats["total_requests"] += 1

            if self.client:
                value = self.client.get(key)
            else:
                # In-memory fallback
                if key in self._memory_cache:
                    cache_item = self._memory_cache[key]
                    if time.time() < cache_item["expires_at"]:
                        value = cache_item["value"]
                    else:
                        del self._memory_cache[key]
                        value = None
                else:
                    value = None

            if value is not None:
                self.stats["hits"] += 1
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                self.stats["misses"] += 1
                logger.debug(f"Cache miss: {key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None

    def delete(self, key: str) -> bool:
        """값 삭제"""
        try:
            if self.client:
                self.client.delete(key)
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear(self) -> bool:
        """전체 캐시 초기화"""
        try:
            if self.client:
                self.client.flushdb()
            else:
                self._memory_cache.clear()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        total = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "status": "connected" if self.client else "in-memory",
        }

    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
        }


# 글로벌 캐시 인스턴스
_cache_instance = None


def get_cache() -> RedisCache:
    """캐시 인스턴스 반환"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
        _cache_instance.connect()
    return _cache_instance


def cache_verdict(func):
    """판정 결과 캐싱 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache = get_cache()

        # 캐시 키 생성
        cache_key = cache._generate_key("verdict", kwargs.get("requirements", {}))

        # 캐시 확인
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 실제 함수 실행
        result = func(*args, **kwargs)

        # 결과 캐싱
        if result is not None:
            cache.set(cache_key, result, cache_type="verdict")

        return result

    return wrapper


def cache_language_info(func):
    """언어 정보 캐싱 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache = get_cache()

        # 언어명에서 캐시 키 생성
        language = args[1] if len(args) > 1 else kwargs.get("language", "")
        cache_key = f"language:{language}"

        # 캐시 확인
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 실제 함수 실행
        result = func(*args, **kwargs)

        # 결과 캐싱
        if result is not None:
            cache.set(cache_key, result, cache_type="language")

        return result

    return wrapper


def cache_comparison(func):
    """언어 비교 결과 캐싱 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache = get_cache()

        # 캐시 키 생성 (언어 목록 기반)
        languages = sorted(kwargs.get("languages", []))
        requirements = kwargs.get("requirements", {})
        cache_data = {"languages": languages, "requirements": requirements}
        cache_key = cache._generate_key("comparison", cache_data)

        # 캐시 확인
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 실제 함수 실행
        result = func(*args, **kwargs)

        # 결과 캐싱
        if result is not None:
            cache.set(cache_key, result, cache_type="comparison")

        return result

    return wrapper


def cache_with_ttl(cache_type: str = "default", ttl: Optional[int] = None):
    """커스텀 TTL을 가진 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # 캐시 키 생성
            cache_key = cache._generate_key(func.__name__, kwargs)

            # 캐시 확인
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 실제 함수 실행
            result = func(*args, **kwargs)

            # 결과 캐싱
            if result is not None:
                cache.set(cache_key, result, ttl=ttl, cache_type=cache_type)

            return result

        return wrapper

    return decorator


class CacheMiddleware:
    """캐시 미들웨어 (FastAPI)"""

    def __init__(self, app):
        """초기화"""
        self.app = app
        self.cache = get_cache()

    async def __call__(self, scope, receive, send):
        """ASGI 미들웨어"""
        if scope["type"] == "http":
            path = scope["path"]

            # 캐시 가능한 엔드포인트
            cacheable_paths = [
                "/api/v2/languages",
                "/api/v2/health",
                "/api/v2/stats",
            ]

            if any(path.startswith(p) for p in cacheable_paths):
                # 캐시 키 생성
                cache_key = f"http:{path}:{scope.get('query_string', b'').decode()}"
                cached_response = self.cache.get(cache_key)

                if cached_response:
                    # 캐시된 응답 반환
                    await send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"application/json"]],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": json.dumps(cached_response).encode(),
                    })
                    return

        await self.app(scope, receive, send)
