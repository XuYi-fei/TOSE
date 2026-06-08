"""Memory usage monitoring for large dataset processing."""

import logging
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


logger = logging.getLogger(__name__)


class MemoryMonitor:
    """
    Monitor memory usage during data processing and warn when approaching limits.

    Example:
        monitor = MemoryMonitor(limit_mb=2048, warn_threshold=0.8)
        for chunk in reader.iter_chunks():
            if monitor.check_memory():
                process(chunk)
            else:
                # Handle memory warning
                break
    """

    def __init__(self, limit_mb: int = 2048, warn_threshold: float = 0.8):
        """
        Initialize memory monitor.

        Args:
            limit_mb: Memory ceiling in MB (default 2048)
            warn_threshold: Warn when memory exceeds this fraction (default 0.8 = 80%)

        Raises:
            ImportError: If psutil is not installed
        """
        if not PSUTIL_AVAILABLE:
            raise ImportError(
                "psutil is required for memory monitoring. "
                "Install it with: pip install psutil"
            )

        self.limit_mb = limit_mb
        self.warn_threshold = warn_threshold
        self.process = psutil.Process()
        self._warned = False

    def get_memory_usage_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            float: Current memory usage in megabytes

        Example:
            monitor = MemoryMonitor()
            usage = monitor.get_memory_usage_mb()
            print(f"Current memory: {usage:.2f} MB")
        """
        return self.process.memory_info().rss / 1024 / 1024

    def check_memory(self) -> bool:
        """
        Check if memory usage is within acceptable range.

        Returns:
            bool: True if memory is OK, False if limit exceeded

        Side effects:
            Logs warning when memory exceeds threshold (once per instance)

        Example:
            monitor = MemoryMonitor(limit_mb=2048, warn_threshold=0.8)
            if not monitor.check_memory():
                print("Memory limit exceeded!")
        """
        current_mb = self.get_memory_usage_mb()
        threshold_mb = self.limit_mb * self.warn_threshold

        if current_mb > threshold_mb and not self._warned:
            percentage = (current_mb / self.limit_mb) * 100
            logger.warning(
                f"Memory usage at {current_mb:.0f}/{self.limit_mb} MB ({percentage:.0f}%). "
                f"Consider reducing chunk size."
            )
            self._warned = True

        return current_mb <= self.limit_mb

    def suggest_chunk_size(self, current_chunk_size: int, target_memory_mb: Optional[float] = None) -> int:
        """
        Suggest reduced chunk size to meet target memory.

        Args:
            current_chunk_size: Current chunk size in rows
            target_memory_mb: Target memory in MB (default: limit_mb * 0.7)

        Returns:
            int: Suggested new chunk size

        Example:
            monitor = MemoryMonitor(limit_mb=2048)
            # If current usage is 1800MB with chunk_size=10000
            new_size = monitor.suggest_chunk_size(10000, target_memory_mb=1400)
            # Returns ~7778 (10000 * 1400/1800)
        """
        if target_memory_mb is None:
            target_memory_mb = self.limit_mb * 0.7

        current_mb = self.get_memory_usage_mb()

        if current_mb <= target_memory_mb:
            return current_chunk_size

        # Linear scaling assumption: chunk_size ∝ memory
        ratio = target_memory_mb / current_mb
        suggested_size = int(current_chunk_size * ratio)

        logger.info(
            f"Suggested chunk size: {suggested_size} "
            f"(reduced from {current_chunk_size} to target {target_memory_mb:.0f}MB)"
        )

        return max(suggested_size, 1000)  # Minimum 1000 rows

    def reset_warning(self):
        """Reset warning flag to allow repeated warnings."""
        self._warned = False

    def get_memory_info(self) -> dict:
        """
        Get detailed memory information.

        Returns:
            dict: Memory info with rss, vms, percent, available

        Example:
            monitor = MemoryMonitor()
            info = monitor.get_memory_info()
            print(f"RSS: {info['rss_mb']:.2f} MB, Percent: {info['percent']:.1f}%")
        """
        mem_info = self.process.memory_info()
        virtual_mem = psutil.virtual_memory()

        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent(),
            'available_mb': virtual_mem.available / 1024 / 1024,
            'total_mb': virtual_mem.total / 1024 / 1024,
            'system_percent': virtual_mem.percent
        }


def monitor_memory_usage(threshold_pct: float = 0.8, limit_mb: int = 2048) -> bool:
    """
    Quick memory check function for use in processing loops.

    Args:
        threshold_pct: Warn when memory exceeds this fraction (default 0.8)
        limit_mb: Memory ceiling in MB (default 2048)

    Returns:
        bool: True if memory is OK, False if limit exceeded

    Example:
        for chunk in chunks:
            if not monitor_memory_usage(threshold_pct=0.8, limit_mb=2048):
                logger.warning("Memory limit reached")
                break
            process(chunk)
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, skipping memory monitoring")
        return True

    monitor = MemoryMonitor(limit_mb=limit_mb, warn_threshold=threshold_pct)
    return monitor.check_memory()
