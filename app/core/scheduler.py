import threading
import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class PeriodicTask:
    """Execute a function periodically on a background thread.
    
    Maintains precise interval timing despite function execution time.
    
    Example:
        def my_task():
            print("Task executed")
        
        task = PeriodicTask(interval_ms=1000, fn=my_task)
        task.start()
        # ... later ...
        task.stop()
    """
    def __init__(self, interval_ms: int, fn: Callable):
        """Initialize periodic task.
        
        Args:
            interval_ms: Execution interval in milliseconds (must be > 0)
            fn: Callable to execute with no arguments
            
        Raises:
            ValueError: If interval_ms is invalid
        """
        if interval_ms <= 0:
            raise ValueError(f"Interval must be positive, got {interval_ms}ms")
        
        self.interval = interval_ms / 1000.0
        self.fn = fn
        self._stop = threading.Event()
        fn_name = getattr(fn, "__name__", repr(fn))
        self._t = threading.Thread(target=self._run, daemon=True, name=f"PeriodicTask-{fn_name}")
        logger.debug(f"PeriodicTask created: {fn_name} every {interval_ms}ms")

    def start(self):
        """Start the periodic task."""
        fn_name = getattr(self.fn, "__name__", repr(self.fn))
        if not self._t.is_alive():
            self._t.start()
            logger.info(f"Started periodic task: {fn_name}")
        else:
            logger.warning(f"Task already running: {fn_name}")

    def stop(self):
        """Stop the periodic task."""
        fn_name = getattr(self.fn, "__name__", repr(self.fn))
        self._stop.set()
        logger.info(f"Stopped periodic task: {fn_name}")

    def _run(self):
        """Internal: main loop (runs in background thread)."""
        fn_name = getattr(self.fn, "__name__", repr(self.fn))
        logger.debug(f"Periodic task loop started: {fn_name}")
        execution_count = 0
        next_t = time.perf_counter()
        
        while not self._stop.is_set():
            now = time.perf_counter()
            if now >= next_t:
                try:
                    exec_start = time.perf_counter()
                    self.fn()
                    exec_time = time.perf_counter() - exec_start
                    execution_count += 1
                    
                    if exec_time > self.interval * 0.5:
                        logger.warning(
                            f"Task {fn_name} took {exec_time*1000:.1f}ms "
                            f"(interval: {self.interval*1000:.1f}ms)"
                        )
                except Exception as e:
                    logger.error(f"Periodic task {fn_name} failed: {e}", exc_info=True)
                
                next_t += self.interval
            else:
                time.sleep(min(0.001, next_t - now))
        
        logger.debug(f"Periodic task loop ended: {fn_name} ({execution_count} executions)")
