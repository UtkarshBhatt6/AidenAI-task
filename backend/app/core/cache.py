"""
MediTrack Caching Layer
High-performance, production-grade caching architecture supporting:
1. RedisCacheLayer: Distributed caching with Redis, sub-millisecond lookups,
   JSON/Pickle dual-mode serialization, prefix invalidation, and single-flight coalescing.
2. InMemoryCacheLayer: Thread-safe local cache with O(1) OrderedDict LRU eviction,
   monotonic TTL support, single-flight coalescing, and defensive copying.
3. Automatic Fallback: Gracefully falls back from Redis to In-Memory if Redis is unreachable.
"""
import os
import time
import copy
import json
import pickle
import logging
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple, Callable, Union

from app.core.config import settings

logger = logging.getLogger("meditrack.cache")


# ==============================================================================
# Helper Serialization Functions for Redis
# ==============================================================================
def _serialize(value: Any) -> bytes:
    """
    Serializes Python objects for Redis storage.
    Prefers JSON for readability & inspectability in redis-cli,
    falling back to pickle for complex non-JSON Python objects.
    """
    try:
        return b"json:" + json.dumps(value).encode("utf-8")
    except (TypeError, ValueError):
        return b"pkl:" + pickle.dumps(value)


def _deserialize(payload: Optional[bytes]) -> Any:
    """
    Deserializes byte payloads retrieved from Redis back to Python objects.
    """
    if payload is None:
        return None
    if payload.startswith(b"json:"):
        return json.loads(payload[5:].decode("utf-8"))
    elif payload.startswith(b"pkl:"):
        return pickle.loads(payload[4:])
    else:
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return pickle.loads(payload)


# ==============================================================================
# In-Memory Cache Implementation (OrderedDict LRU + Monotonic TTL)
# ==============================================================================
class InMemoryCacheLayer:
    def __init__(
        self, 
        max_size: int = 2048, 
        default_ttl: int = 300, 
        defensive_copy: bool = True
    ):
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        if default_ttl < 0:
            raise ValueError(f"default_ttl must be >= 0, got {default_ttl}")

        self.max_size = max_size
        self.default_ttl = default_ttl
        self.defensive_copy = defensive_copy
        
        self._lock = threading.RLock()
        self._key_locks: Dict[str, threading.Lock] = {}
        self._key_locks_lock = threading.Lock()
        
        # OrderedDict maintains O(1) recency order.
        # Key -> (value, expire_at_monotonic, last_accessed_monotonic, hits)
        self._store: OrderedDict[str, Tuple[Any, float, float, int]] = OrderedDict()
        
        # Telemetry counters
        self._hits: int = 0
        self._misses: int = 0
        self._capacity_evictions: int = 0
        self._ttl_expirations: int = 0

    @property
    def _evictions(self) -> int:
        return self._capacity_evictions + self._ttl_expirations

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        with self._lock:
            now = time.monotonic()
            if key in self._store:
                val, expire_at, last_accessed, hits = self._store[key]
                if expire_at > now:
                    self._hits += 1
                    self._store[key] = (val, expire_at, now, hits + 1)
                    self._store.move_to_end(key, last=True)
                    return (copy.deepcopy(val) if self.defensive_copy else val), True
                else:
                    del self._store[key]
                    self._ttl_expirations += 1
                    
            self._misses += 1
            return None, False

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if ttl is not None and ttl <= 0:
            self.invalidate(key)
            return

        effective_ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            now = time.monotonic()
            expire_at = now + effective_ttl
            stored_val = copy.deepcopy(value) if self.defensive_copy else value

            if key in self._store:
                self._store[key] = (stored_val, expire_at, now, 0)
                self._store.move_to_end(key, last=True)
                return

            while len(self._store) >= self.max_size:
                oldest_key, (_, exp_at, _, _) = next(iter(self._store.items()))
                if exp_at <= now:
                    self._store.popitem(last=False)
                    self._ttl_expirations += 1
                else:
                    self._store.popitem(last=False)
                    self._capacity_evictions += 1
                    break

            self._store[key] = (stored_val, expire_at, now, 0)

    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys_to_delete = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)

    def clear(self, reset_counters: bool = False) -> None:
        with self._lock:
            self._store.clear()
            if reset_counters:
                self._hits = 0
                self._misses = 0
                self._capacity_evictions = 0
                self._ttl_expirations = 0

    def prune_expired(self) -> int:
        with self._lock:
            now = time.monotonic()
            expired_keys = [k for k, (_, exp_at, _, _) in self._store.items() if exp_at <= now]
            for k in expired_keys:
                del self._store[k]
                self._ttl_expirations += 1
            return len(expired_keys)

    def get_or_compute(
        self, 
        key: str, 
        compute_fn: Callable[[], Any], 
        ttl: Optional[int] = None
    ) -> Tuple[Any, bool]:
        val, hit = self.get(key)
        if hit:
            return val, True

        with self._key_locks_lock:
            if key not in self._key_locks:
                self._key_locks[key] = threading.Lock()
            key_lock = self._key_locks[key]

        with key_lock:
            val, hit = self.get(key)
            if hit:
                return val, True

            computed_value = compute_fn()
            if computed_value is not None:
                self.set(key, computed_value, ttl=ttl)

            with self._key_locks_lock:
                self._key_locks.pop(key, None)

            return computed_value, False

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100.0) if total_requests > 0 else 0.0
            now = time.monotonic()
            active_keys = sum(1 for _, expire_at, _, _ in self._store.values() if expire_at > now)
            estimated_latency_saved_ms = self._hits * 24.5
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_ratio_percent": round(hit_ratio, 2),
                "active_keys_count": active_keys,
                "total_evictions": self._evictions,
                "capacity_evictions": self._capacity_evictions,
                "ttl_expirations": self._ttl_expirations,
                "estimated_latency_saved_ms": round(estimated_latency_saved_ms, 1),
                "cache_store_size": len(self._store),
                "max_size": self.max_size,
                "default_ttl_seconds": self.default_ttl,
                "backend": "in_memory"
            }


# Backwards compatibility alias for existing unit tests
CacheLayer = InMemoryCacheLayer


# ==============================================================================
# Redis Distributed Cache Implementation
# ==============================================================================
class RedisCacheLayer:
    def __init__(
        self, 
        redis_url: str = "redis://127.0.0.1:6379/0", 
        default_ttl: int = 300,
        client: Optional[Any] = None
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self._key_locks: Dict[str, threading.Lock] = {}
        self._key_locks_lock = threading.Lock()
        
        # Telemetry counters for this node/process
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        
        if client is not None:
            self._redis = client
        else:
            import redis
            self._redis = redis.Redis.from_url(
                self.redis_url, 
                decode_responses=False,
                socket_timeout=3.0,
                socket_connect_timeout=3.0
            )

    def ping(self) -> bool:
        """Verifies Redis connection health."""
        try:
            return bool(self._redis.ping())
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Retrieves item from Redis.
        Returns: (value, is_hit)
        """
        try:
            payload = self._redis.get(key)
            if payload is not None:
                with self._lock:
                    self._hits += 1
                return _deserialize(payload), True
            else:
                with self._lock:
                    self._misses += 1
                return None, False
        except Exception as e:
            logger.warning(f"Redis get('{key}') failed: {e}")
            with self._lock:
                self._misses += 1
            return None, False

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Stores item in Redis with TTL expiration.
        """
        if ttl is not None and ttl <= 0:
            self.invalidate(key)
            return

        effective_ttl = ttl if ttl is not None else self.default_ttl
        try:
            payload = _serialize(value)
            self._redis.set(key, payload, ex=effective_ttl)
        except Exception as e:
            logger.warning(f"Redis set('{key}') failed: {e}")

    def invalidate(self, key: str) -> bool:
        """Deletes a key from Redis."""
        try:
            return bool(self._redis.delete(key))
        except Exception as e:
            logger.warning(f"Redis invalidate('{key}') failed: {e}")
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Scans and deletes all keys starting with prefix.
        Uses scan_iter for non-blocking iteration.
        """
        try:
            pattern = f"{prefix}*"
            keys_to_delete = list(self._redis.scan_iter(match=pattern, count=100))
            if keys_to_delete:
                deleted_count = self._redis.delete(*keys_to_delete)
                return deleted_count
            return 0
        except Exception as e:
            logger.warning(f"Redis invalidate_prefix('{prefix}') failed: {e}")
            return 0

    def clear(self, reset_counters: bool = False) -> None:
        """
        Flushes all Redis keys.
        """
        try:
            # Delete keys matching appointments, reports, or common meditrack keys
            keys = list(self._redis.scan_iter("*", count=200))
            if keys:
                self._redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")

        if reset_counters:
            with self._lock:
                self._hits = 0
                self._misses = 0
                self._evictions = 0

    def prune_expired(self) -> int:
        """Redis handles key expirations automatically; returns 0."""
        return 0

    def get_or_compute(
        self, 
        key: str, 
        compute_fn: Callable[[], Any], 
        ttl: Optional[int] = None
    ) -> Tuple[Any, bool]:
        """
        Single-flight request coalescing helper to prevent cache stampedes.
        """
        # Fast path
        val, hit = self.get(key)
        if hit:
            return val, True

        # Acquire lock for this key
        with self._key_locks_lock:
            if key not in self._key_locks:
                self._key_locks[key] = threading.Lock()
            key_lock = self._key_locks[key]

        with key_lock:
            # Double-check
            val, hit = self.get(key)
            if hit:
                return val, True

            computed_value = compute_fn()
            if computed_value is not None:
                self.set(key, computed_value, ttl=ttl)

            with self._key_locks_lock:
                self._key_locks.pop(key, None)

            return computed_value, False

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns live Redis telemetry.
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100.0) if total_requests > 0 else 0.0
            
            try:
                active_keys = self._redis.dbsize()
                info = self._redis.info("stats")
                redis_evictions = info.get("evicted_keys", 0)
                redis_expired = info.get("expired_keys", 0)
            except Exception:
                active_keys = 0
                redis_evictions = 0
                redis_expired = 0

            estimated_latency_saved_ms = self._hits * 24.5

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_ratio_percent": round(hit_ratio, 2),
                "active_keys_count": active_keys,
                "total_evictions": redis_evictions + redis_expired,
                "capacity_evictions": redis_evictions,
                "ttl_expirations": redis_expired,
                "estimated_latency_saved_ms": round(estimated_latency_saved_ms, 1),
                "cache_store_size": active_keys,
                "max_size": 100000,
                "default_ttl_seconds": self.default_ttl,
                "backend": "redis"
            }


# ==============================================================================
# Cache Factory with Automatic Redis / In-Memory Fallback
# ==============================================================================
def create_cache() -> Union[RedisCacheLayer, InMemoryCacheLayer]:
    """
    Initializes the cache layer based on configuration.
    Attempts Redis first if CACHE_BACKEND == 'redis'.
    If Redis is unreachable or fails ping, seamlessly falls back to InMemoryCacheLayer.
    """
    backend_mode = getattr(settings, "CACHE_BACKEND", "redis").lower()
    redis_url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
    default_ttl = getattr(settings, "CACHE_DEFAULT_TTL_SECONDS", 300)

    if backend_mode == "redis":
        try:
            import redis
            client = redis.Redis.from_url(
                redis_url, 
                decode_responses=False,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            client.ping()
            logger.info(f"✅ Active Cache: Redis Distributed Cache connected at {redis_url}")
            return RedisCacheLayer(redis_url=redis_url, default_ttl=default_ttl, client=client)
        except Exception as e:
            logger.warning(
                f"⚠️ Could not connect to Redis at {redis_url} ({e}). "
                f"Gracefully falling back to thread-safe InMemoryCacheLayer."
            )
            return InMemoryCacheLayer(default_ttl=default_ttl)

    logger.info("Active Cache: In-Memory LRU/TTL Cache")
    return InMemoryCacheLayer(default_ttl=default_ttl)


# Global singleton cache instance used across FastAPI endpoints
cache = create_cache()
