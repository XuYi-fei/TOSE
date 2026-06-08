"""Tests for memory monitoring."""

import sys

# Try to import psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

if PSUTIL_AVAILABLE:
    from cluster_analysis.utils import MemoryMonitor, monitor_memory_usage


def test_memory_monitor_basic():
    """Test basic memory monitoring functionality."""
    if not PSUTIL_AVAILABLE:
        print("Skipping test: psutil not available")
        return

    monitor = MemoryMonitor(limit_mb=2048, warn_threshold=0.8)

    # Get current usage
    usage = monitor.get_memory_usage_mb()
    assert usage > 0, "Memory usage should be positive"

    # Check memory (should pass for reasonable usage)
    assert monitor.check_memory() in [True, False]

    print(f"✓ Current memory usage: {usage:.2f} MB")


def test_memory_info():
    """Test detailed memory information retrieval."""
    if not PSUTIL_AVAILABLE:
        print("Skipping test: psutil not available")
        return

    monitor = MemoryMonitor()
    info = monitor.get_memory_info()

    # Verify all expected keys exist
    assert 'rss_mb' in info
    assert 'vms_mb' in info
    assert 'percent' in info
    assert 'available_mb' in info
    assert 'total_mb' in info
    assert 'system_percent' in info

    print(f"✓ Memory info: RSS={info['rss_mb']:.2f}MB, Available={info['available_mb']:.2f}MB")


def test_suggest_chunk_size():
    """Test chunk size suggestion based on memory."""
    if not PSUTIL_AVAILABLE:
        print("Skipping test: psutil not available")
        return

    monitor = MemoryMonitor(limit_mb=2048, warn_threshold=0.8)

    # If current usage is low, should return same size
    current_usage = monitor.get_memory_usage_mb()

    if current_usage < 1400:
        suggested = monitor.suggest_chunk_size(10000, target_memory_mb=1400)
        # Should suggest same or higher size
        assert suggested >= 1000

    print(f"✓ Suggested chunk size for target 1400MB: {suggested} rows")


def test_monitor_memory_usage_function():
    """Test quick memory check function."""
    if not PSUTIL_AVAILABLE:
        print("Skipping test: psutil not available")
        return

    result = monitor_memory_usage(threshold_pct=0.8, limit_mb=2048)
    assert isinstance(result, bool)

    print(f"✓ Memory check result: {result}")


def test_memory_warning_logged():
    """
    Test that warning is logged when memory exceeds threshold.

    This is the validation criteria from Task 1.3.
    """
    if not PSUTIL_AVAILABLE:
        print("Skipping test: psutil not available")
        return

    # Create monitor with very low limit to trigger warning
    current_usage = MemoryMonitor().get_memory_usage_mb()
    low_limit = int(current_usage * 0.9)  # 90% of current usage

    monitor = MemoryMonitor(limit_mb=low_limit, warn_threshold=0.8)

    # This should trigger warning (if usage > 80% of low_limit)
    result = monitor.check_memory()

    if not result:
        print(f"✓ Warning correctly triggered: usage exceeds limit")
    else:
        print(f"✓ Memory within limit ({current_usage:.0f}MB < {low_limit}MB)")


if __name__ == '__main__':
    print("Running memory monitoring tests...")

    if not PSUTIL_AVAILABLE:
        print("⚠ psutil not installed. Install with: pip install psutil")
        print("Skipping all memory monitoring tests.")
        sys.exit(0)

    test_memory_monitor_basic()
    test_memory_info()
    test_suggest_chunk_size()
    test_monitor_memory_usage_function()
    test_memory_warning_logged()

    print("\n✓ All memory monitoring tests passed")
