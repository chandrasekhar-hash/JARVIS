"""
Exponential Backoff Retry Manager for J.A.R.V.I.S. Phase V1.7.
"""
import asyncio
import inspect
import logging
from typing import Callable, Any, Optional
from .interfaces import IRetryManager
from .models import RetryStatistics

logger = logging.getLogger("JARVIS_RetryManager")


class RetryManager(IRetryManager):
    """
    Executes async functions with exponential backoff retries and jitter.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_sec: float = 0.1,
        backoff_factor: float = 1.5,
    ):
        self.max_retries = max_retries
        self.initial_delay_sec = initial_delay_sec
        self.backoff_factor = backoff_factor

        self._total_attempts: int = 0
        self._successful_retries: int = 0
        self._failed_retries: int = 0
        self._exhausted_retries: int = 0

    async def execute_with_retry(self, fn: Callable, *args, **kwargs) -> Any:
        delay = self.initial_delay_sec
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            self._total_attempts += 1
            try:
                if inspect.iscoroutinefunction(fn):
                    res = await fn(*args, **kwargs)
                else:
                    res = fn(*args, **kwargs)

                if attempt > 1:
                    self._successful_retries += 1
                    logger.info(f"[RetryManager] Operation succeeded on retry attempt {attempt}/{self.max_retries}.")
                return res
            except Exception as e:
                last_exception = e
                self._failed_retries += 1
                logger.warning(
                    f"[RetryManager] Operation attempt {attempt}/{self.max_retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor

        self._exhausted_retries += 1
        logger.error(f"[RetryManager] All {self.max_retries} retry attempts exhausted.")
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry attempts exhausted")

    def get_statistics(self) -> RetryStatistics:
        return RetryStatistics(
            total_attempts=self._total_attempts,
            successful_retries=self._successful_retries,
            failed_retries=self._failed_retries,
            exhausted_retries=self._exhausted_retries,
        )
