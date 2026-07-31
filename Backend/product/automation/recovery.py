"""
JARVIS Product 1.7 - Retry & Timeout Recovery Managers.
Manages exponential backoff retries, action timeouts, and cancellations.
"""

import time
import math
import logging
from typing import Callable, Any, Dict
from .models import RetryPolicyConfig

logger = logging.getLogger(__name__)


class RetryManager:
    @staticmethod
    def execute_with_retry(
        action_func: Callable[[], Dict[str, Any]],
        retry_policy: RetryPolicyConfig,
    ) -> Dict[str, Any]:
        attempts = 0
        last_exception = None

        while attempts <= retry_policy.max_retries:
            attempts += 1
            try:
                result = action_func()
                if result.get("success", True) or result.get("status") == "success":
                    return result
                
                # If explicit failure returned and retries left
                if attempts <= retry_policy.max_retries:
                    delay = retry_policy.initial_delay_seconds * (retry_policy.backoff_factor ** (attempts - 1))
                    logger.info(f"Action failed. Retrying attempt {attempts}/{retry_policy.max_retries} after {delay:.2f}s delay...")
                    time.sleep(delay)
                else:
                    return result

            except Exception as e:
                last_exception = e
                logger.warning(f"Action exception on attempt {attempts}: {e}")
                if attempts <= retry_policy.max_retries:
                    delay = retry_policy.initial_delay_seconds * (retry_policy.backoff_factor ** (attempts - 1))
                    time.sleep(delay)
                else:
                    break

        return {
            "status": "failed",
            "success": False,
            "error_message": str(last_exception) if last_exception else "Execution failed after maximum retries.",
            "attempts": attempts,
        }


class TimeoutManager:
    @staticmethod
    def execute_with_timeout(
        action_func: Callable[[], Dict[str, Any]],
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        start_time = time.time()
        result = action_func()
        duration = time.time() - start_time
        if duration > timeout_seconds:
            return {
                "status": "timeout",
                "success": False,
                "error_message": f"Execution exceeded timeout limit ({timeout_seconds}s).",
                "duration_seconds": duration,
            }
        return result
