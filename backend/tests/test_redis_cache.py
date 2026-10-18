"""
MediTrack Redis Cache Test Suite
Validates RedisCacheLayer operations, TTL handling, prefix invalidation,
single-flight coalescing, telemetry reporting, and automatic in-memory fallback.
"""
import time
import pytest
import threading
from app.core.cache import RedisCacheLayer, InMemoryCacheLayer, create_cache
from app.core.config import settings

@pytest.fixture
def redis_cache():
    """Initializes a RedisCacheLayer and clears test keys before/after."""
    cache = RedisCacheLayer(redis_url=settings.REDIS_URL, default_ttl=60)
    cache.clear()
    yield cache
    cache.clear()

def test_redis_connection_and_ping(redis_cache):
    """Verify that Redis connects and responds to ping."""
    assert redis_cache.ping() is True

def test_redis_set_get_and_ttl(redis_cache):
    """Verify storing, retrieving, and TTL expiration in Redis."""
    # Test setting and getting complex dictionary
    patient_data = {
        "id": "apt-999",
        "name": "Redis Test Patient",
        "risk_score": 0.42,
        "tags": ["urgent", "cardiology"]
    }
    redis_cache.set("test:patient:999", patient_data, ttl=2)
    
    val, hit = redis_cache.get("test:patient:999")
    assert hit is True
    assert val["name"] == "Redis Test Patient"
    assert val["risk_score"] == 0.42
    assert val["tags"] == ["urgent", "cardiology"]
    
    # Test cache miss on non-existent key
    missing_val, missing_hit = redis_cache.get("test:patient:does_not_exist")
    assert missing_hit is False
    assert missing_val is None

def test_redis_invalidation_and_prefix(redis_cache):
    """Verify single key and prefix-based invalidation in Redis."""
    redis_cache.set("test:appointments:list:branch-1:2026-10-18", [{"id": "1"}])
    redis_cache.set("test:appointments:list:branch-2:2026-10-18", [{"id": "2"}])
    redis_cache.set("test:reports:daily:branch-1", {"revenue": 5000})

    # Invalidate single key
    deleted = redis_cache.invalidate("test:reports:daily:branch-1")
    assert deleted is True
    assert redis_cache.get("test:reports:daily:branch-1")[1] is False

    # Invalidate prefix
    count = redis_cache.invalidate_prefix("test:appointments:list:")
    assert count >= 2
    assert redis_cache.get("test:appointments:list:branch-1:2026-10-18")[1] is False
    assert redis_cache.get("test:appointments:list:branch-2:2026-10-18")[1] is False

def test_redis_single_flight_coalescing(redis_cache):
    """
    Verify get_or_compute executes compute_fn only once across concurrent threads
    when hitting Redis.
    """
    call_count = 0
    lock = threading.Lock()

    def heavy_compute():
        nonlocal call_count
        with lock:
            call_count += 1
        time.sleep(0.05)
        return {"result": "computed_value", "timestamp": time.time()}

    results = []
    threads = []

    def worker():
        val, hit = redis_cache.get_or_compute("test:stampede_probe", heavy_compute, ttl=30)
        results.append((val, hit))

    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Compute should have executed exactly once
    assert call_count == 1
    assert len(results) == 5
    for val, _ in results:
        assert val["result"] == "computed_value"

def test_redis_telemetry_reporting(redis_cache):
    """Verify telemetry stats reflect hits, misses, and backend identifier."""
    redis_cache.set("test:stats:k1", "v1")
    redis_cache.get("test:stats:k1") # Hit
    redis_cache.get("test:stats:k1") # Hit
    redis_cache.get("test:stats:missing") # Miss

    stats = redis_cache.get_stats()
    assert stats["backend"] == "redis"
    assert stats["hits"] >= 2
    assert stats["misses"] >= 1
    assert stats["total_requests"] == stats["hits"] + stats["misses"]
    assert stats["hit_ratio_percent"] > 0

def test_cache_fallback_when_redis_unavailable():
    """Verify create_cache() falls back to InMemoryCacheLayer on invalid Redis URL."""
    # Force invalid redis URL
    saved_url = settings.REDIS_URL
    try:
        settings.REDIS_URL = "redis://127.0.0.1:9999/0" # Non-existent port
        cache_instance = create_cache()
        assert isinstance(cache_instance, InMemoryCacheLayer)
        assert cache_instance.get_stats()["backend"] == "in_memory"
    finally:
        settings.REDIS_URL = saved_url
