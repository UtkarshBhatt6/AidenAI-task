"""
MediTrack Caching Layer
High-performance, thread-safe in-memory cache with TTL support,
LRU eviction, hit/miss telemetry, and prefix-based invalidation.
"""
import time
import threading
from typing import Any, Optional, Dict, Tuple

class CacheLayer:
    def __init__(self, max_size: int = 2048, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        # key -> (value, expire_at, last_accessed, hits)
        self._store: Dict[str, Tuple[Any, float, float, int]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Retrieves an item from cache.
        Returns: (value, is_hit)
        """
        with self._lock:
            now = time.time()
            if key in self._store:
                val, expire_at, last_accessed, hits = self._store[key]
                if expire_at > now:
                    self._hits += 1
                    # Update LRU metadata
                    self._store[key] = (val, expire_at, now, hits + 1)
                    return val, True
                else:
                    # Expired
                    del self._store[key]
                    self._evictions += 1
                    
            self._misses += 1
            return None, False
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Stores an item with TTL. Evicts least recently used if exceeding max_size.
        """
        with self._lock:
            now = time.time()
            expire_at = now + (ttl if ttl is not None else self.default_ttl)
            
            # Enforce max size via LRU eviction
            if len(self._store) >= self.max_size and key not in self._store:
                # Find key with oldest last_accessed
                lru_key = min(self._store.keys(), key=lambda k: self._store[k][2])
                del self._store[lru_key]
                self._evictions += 1
                
            self._store[key] = (value, expire_at, now, 0)
            
    def invalidate(self, key: str) -> bool:
        """
        Deletes a specific cache key.
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
            
    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidates all keys matching a prefix.
        Used when modifying appointments to invalidate list queries and reports.
        """
        with self._lock:
            keys_to_delete = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)
            
    def clear(self) -> None:
        """
        Flushes entire cache and resets counters (except lifetime metrics if desired).
        """
        with self._lock:
            self._store.clear()
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Returns telemetry regarding cache utilization, hit rates, and key counts.
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100.0) if total_requests > 0 else 0.0
            now = time.time()
            active_keys = sum(1 for _, expire_at, _, _ in self._store.values() if expire_at > now)
            
            # Estimate latency saved (assuming avg DB read takes ~25ms vs cache <0.5ms)
            estimated_latency_saved_ms = self._hits * 24.5
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_ratio_percent": round(hit_ratio, 2),
                "active_keys_count": active_keys,
                "total_evictions": self._evictions,
                "estimated_latency_saved_ms": round(estimated_latency_saved_ms, 1),
                "cache_store_size": len(self._store),
                "max_size": self.max_size,
                "default_ttl_seconds": self.default_ttl
            }

# Global singleton cache instance
cache = CacheLayer()
