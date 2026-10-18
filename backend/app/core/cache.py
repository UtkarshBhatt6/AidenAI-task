"""
MediTrack Caching Layer
High-performance, thread-safe in-memory cache with monotonic TTL support,
O(1) OrderedDict LRU eviction, single-flight request coalescing,
defensive copying, granular telemetry, and prefix-based invalidation.
"""
import time
import copy
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple, Callable

class CacheLayer:
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
        # Front (last=False) is LRU; End (last=True) is MRU.
        self._store: OrderedDict[str, Tuple[Any, float, float, int]] = OrderedDict()
        
        # Telemetry counters
        self._hits: int = 0
        self._misses: int = 0
        self._capacity_evictions: int = 0
        self._ttl_expirations: int = 0

    @property
    def _evictions(self) -> int:
        """Total evictions (capacity overflows + expired item purges) for backwards compatibility."""
        return self._capacity_evictions + self._ttl_expirations

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Retrieves an item from cache.
        Returns: (value, is_hit)
        
        - If key exists and unexpired: marks as MRU in O(1) and returns (value, True).
        - If key exists but expired: deletes entry, records TTL expiration, returns (None, False).
        - If key absent: returns (None, False).
        """
        with self._lock:
            now = time.monotonic()
            if key in self._store:
                val, expire_at, last_accessed, hits = self._store[key]
                if expire_at > now:
                    self._hits += 1
                    # Update O(1) LRU order: move to end (MRU)
                    self._store[key] = (val, expire_at, now, hits + 1)
                    self._store.move_to_end(key, last=True)
                    
                    return (copy.deepcopy(val) if self.defensive_copy else val), True
                else:
                    # Expired entry discovered lazily
                    del self._store[key]
                    self._ttl_expirations += 1
                    
            self._misses += 1
            return None, False

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Stores an item with TTL.
        Enforces O(1) LRU eviction when capacity is exceeded.
        Prunes expired entries first before evicting valid LRU items.
        """
        if ttl is not None and ttl <= 0:
            # Non-positive TTL: treat as immediate invalidation/no-op
            self.invalidate(key)
            return

        effective_ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            now = time.monotonic()
            expire_at = now + effective_ttl
            stored_val = copy.deepcopy(value) if self.defensive_copy else value

            # If key already exists, update and move to MRU
            if key in self._store:
                self._store[key] = (stored_val, expire_at, now, 0)
                self._store.move_to_end(key, last=True)
                return

            # Capacity check: If full, first try to prune an expired item from the LRU end
            while len(self._store) >= self.max_size:
                oldest_key, (_, exp_at, _, _) = next(iter(self._store.items()))
                if exp_at <= now:
                    # Oldest item is already expired; purge it as a TTL expiration in O(1)
                    self._store.popitem(last=False)
                    self._ttl_expirations += 1
                else:
                    # Oldest item is valid; must evict as a true LRU capacity eviction in O(1)
                    self._store.popitem(last=False)
                    self._capacity_evictions += 1
                    break

            # Insert new key at MRU end in O(1)
            self._store[key] = (stored_val, expire_at, now, 0)

    def invalidate(self, key: str) -> bool:
        """
        Deletes a specific cache key in O(1).
        Returns True if the key was present, False otherwise.
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidates all keys matching a string prefix.
        Used when modifying appointments to invalidate list queries and reports.
        """
        with self._lock:
            keys_to_delete = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)

    def clear(self, reset_counters: bool = False) -> None:
        """
        Flushes all entries from the cache.
        
        Args:
            reset_counters: If True, resets all hit/miss/eviction counters to 0.
                           If False (default), retains lifetime telemetry for monitoring.
        """
        with self._lock:
            self._store.clear()
            if reset_counters:
                self._hits = 0
                self._misses = 0
                self._capacity_evictions = 0
                self._ttl_expirations = 0

    def prune_expired(self) -> int:
        """
        Actively prunes all expired entries currently stored in the cache.
        Returns the number of pruned expired entries.
        """
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
        """
        Single-flight cache-aside helper to mitigate cache stampedes.
        If cache misses, only ONE thread executes compute_fn() for this key;
        concurrent requests wait on a per-key lock and read the cached result.
        """
        # Fast path: check cache first
        val, hit = self.get(key)
        if hit:
            return val, True

        # Acquire per-key lock to prevent cache stampede
        with self._key_locks_lock:
            if key not in self._key_locks:
                self._key_locks[key] = threading.Lock()
            key_lock = self._key_locks[key]

        with key_lock:
            # Double-check cache inside per-key lock
            val, hit = self.get(key)
            if hit:
                return val, True

            # Compute value from data source (e.g. database)
            computed_value = compute_fn()
            if computed_value is not None:
                self.set(key, computed_value, ttl=ttl)

            # Cleanup per-key lock reference to avoid memory growth
            with self._key_locks_lock:
                self._key_locks.pop(key, None)

            return computed_value, False

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns telemetry regarding cache utilization, hit rates, and key counts.
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100.0) if total_requests > 0 else 0.0
            now = time.monotonic()
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
                "capacity_evictions": self._capacity_evictions,
                "ttl_expirations": self._ttl_expirations,
                "estimated_latency_saved_ms": round(estimated_latency_saved_ms, 1),
                "cache_store_size": len(self._store),
                "max_size": self.max_size,
                "default_ttl_seconds": self.default_ttl
            }

# Global singleton cache instance
cache = CacheLayer()
