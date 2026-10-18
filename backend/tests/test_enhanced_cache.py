"""
Unit tests for the enhanced production-grade CacheLayer
Validates O(1) OrderedDict LRU, monotonic TTL, single-flight coalescing,
defensive copying, telemetry breakdown, and input validation.
"""
import time
import pytest
import threading
from app.core.cache import CacheLayer

def test_cache_input_validation():
    """Verify max_size and default_ttl guardrails."""
    with pytest.raises(ValueError, match="max_size must be >= 1"):
        CacheLayer(max_size=0)
        
    with pytest.raises(ValueError, match="max_size must be >= 1"):
        CacheLayer(max_size=-5)

    with pytest.raises(ValueError, match="default_ttl must be >= 0"):
        CacheLayer(default_ttl=-1)

def test_lru_eviction_order():
    """
    Verify strict O(1) LRU eviction order with capacity of 3.
    1. Insert A, B, C
    2. Read A (A becomes MRU, B is now LRU)
    3. Insert D (B must be evicted)
    """
    c = CacheLayer(max_size=3, default_ttl=60)
    c.set("A", "val_A")
    c.set("B", "val_B")
    c.set("C", "val_C")
    
    # Access A -> order is now B (LRU), C, A (MRU)
    val_a, hit_a = c.get("A")
    assert hit_a is True
    assert val_a == "val_A"
    
    # Insert D -> should evict B
    c.set("D", "val_D")
    
    # B should be evicted
    val_b, hit_b = c.get("B")
    assert hit_b is False
    assert val_b is None
    
    # C, A, D should still exist
    assert c.get("C")[1] is True
    assert c.get("A")[1] is True
    assert c.get("D")[1] is True
    
    stats = c.get_stats()
    assert stats["capacity_evictions"] == 1
    assert stats["ttl_expirations"] == 0
    assert stats["total_evictions"] == 1

def test_expired_entry_purged_before_valid_eviction():
    """
    If capacity is full, but the oldest entry has expired,
    purging it preserves valid entries.
    """
    c = CacheLayer(max_size=2, default_ttl=60)
    # Insert A with very short TTL
    c.set("A", "val_A", ttl=0.1) # 100ms
    # Insert B with normal TTL
    c.set("B", "val_B", ttl=60)
    
    time.sleep(0.15) # Wait for A to expire
    
    # Insert C: Capacity is 2, store has A (expired) and B (valid)
    c.set("C", "val_C", ttl=60)
    
    # B should NOT be evicted because A was purged first
    assert c.get("B")[1] is True
    assert c.get("C")[1] is True
    assert c.get("A")[1] is False
    
    stats = c.get_stats()
    assert stats["ttl_expirations"] >= 1
    assert stats["capacity_evictions"] == 0

def test_defensive_copying_prevents_caller_mutation():
    """Verify modifying a retrieved or stored dictionary does not mutate the cache."""
    c = CacheLayer(max_size=10, default_ttl=60, defensive_copy=True)
    original = {"appointment_id": "apt-101", "status": "SCHEDULED"}
    c.set("apt-101", original)
    
    # Mutate original outside cache
    original["status"] = "CANCELLED"
    
    cached, hit = c.get("apt-101")
    assert hit is True
    assert cached["status"] == "SCHEDULED" # Cache protected from caller mutation
    
    # Mutate returned object
    cached["status"] = "COMPLETED"
    
    cached2, _ = c.get("apt-101")
    assert cached2["status"] == "SCHEDULED" # Cache protected from return value mutation

def test_clear_with_and_without_resetting_counters():
    """Verify clear(reset_counters=False) vs clear(reset_counters=True)."""
    c = CacheLayer(max_size=10, default_ttl=60)
    c.set("k1", "v1")
    c.get("k1") # 1 hit
    c.get("missing") # 1 miss
    
    stats_before = c.get_stats()
    assert stats_before["hits"] == 1
    assert stats_before["misses"] == 1
    assert stats_before["cache_store_size"] == 1
    
    # Clear without resetting counters (default)
    c.clear(reset_counters=False)
    stats_after_preserve = c.get_stats()
    assert stats_after_preserve["cache_store_size"] == 0
    assert stats_after_preserve["hits"] == 1
    assert stats_after_preserve["misses"] == 1
    
    # Clear with resetting counters
    c.clear(reset_counters=True)
    stats_after_reset = c.get_stats()
    assert stats_after_reset["cache_store_size"] == 0
    assert stats_after_reset["hits"] == 0
    assert stats_after_reset["misses"] == 0

def test_single_flight_coalescing():
    """
    Verify get_or_compute executes compute_fn only once across concurrent threads.
    """
    c = CacheLayer(max_size=10, default_ttl=60)
    call_count = 0
    lock = threading.Lock()
    
    def slow_compute():
        nonlocal call_count
        with lock:
            call_count += 1
        time.sleep(0.05) # simulate DB query latency
        return {"report_date": "2026-10-18", "total": 42}
        
    results = []
    threads = []
    
    def worker():
        val, hit = c.get_or_compute("daily_report", slow_compute)
        results.append((val, hit))
        
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # compute_fn should only have been called ONCE
    assert call_count == 1
    assert len(results) == 5
    for val, _ in results:
        assert val["total"] == 42
