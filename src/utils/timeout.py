"""Timeout utilities for preventing I/O hangs."""

import logging
import signal
import threading
from contextlib import contextmanager
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


@contextmanager
def timeout_guard(seconds: float, operation_name: str = "operation"):
    """
    Context manager that raises TimeoutError if the block takes longer than specified.

    Uses SIGALRM on Unix systems. Only works in the main thread.

    Args:
        seconds: Maximum time to allow
        operation_name: Description of operation for logging

    Raises:
        TimeoutError: If operation exceeds timeout

    Example:
        with timeout_guard(2.0, "serial write"):
            device.write(data)
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"{operation_name} timed out after {seconds}s")

    # Only works in main thread on Unix
    if threading.current_thread() is not threading.main_thread():
        logger.warning(f"timeout_guard for '{operation_name}' called from non-main thread, timeout disabled")
        yield
        return

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)

    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def call_with_timeout(func: Callable, timeout: float, operation_name: str = "operation",
                     default: Any = None) -> Any:
    """
    Call a function with a timeout, returning default value if it times out.

    Args:
        func: Function to call (must be callable with no arguments)
        timeout: Maximum time to allow in seconds
        operation_name: Description for logging
        default: Value to return on timeout

    Returns:
        Function result or default if timeout occurs
    """
    try:
        with timeout_guard(timeout, operation_name):
            return func()
    except TimeoutError:
        logger.error(f"{operation_name} timed out after {timeout}s, returning default")
        return default
    except Exception as e:
        logger.error(f"{operation_name} failed: {e}")
        return default
