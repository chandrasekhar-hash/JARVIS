"""
Product 1.5 Retry Policy & Backoff Algorithms.
"""
import random
import logging
from typing import Tuple, Optional, Any
from .models import RetryPolicy, RetryPolicyType

logger = logging.getLogger("JARVIS_RetryManager")


class RetryManager:
    """
    Evaluates retry eligibility and computes backoff delays with jitter.
    """

    @staticmethod
    def should_retry(
        policy: RetryPolicy,
        current_attempt: int,
        exception: Exception,
    ) -> Tuple[bool, float]:
        """
        Determines if execution should be retried and returns backoff delay in seconds.
        Returns:
            (should_retry, delay_seconds)
        """
        if policy.policy_type == RetryPolicyType.NEVER:
            return False, 0.0

        if current_attempt >= policy.max_retries:
            logger.info(f"[RetryManager] Retry limit reached ({current_attempt}/{policy.max_retries}). Aborting retries.")
            return False, 0.0

        # Check exception filter if specified
        if policy.retryable_exceptions:
            exc_name = type(exception).__name__
            if exc_name not in policy.retryable_exceptions and "Exception" not in policy.retryable_exceptions:
                logger.info(f"[RetryManager] Exception '{exc_name}' is not marked retryable in policy. Aborting retries.")
                return False, 0.0

        if policy.policy_type == RetryPolicyType.FIXED:
            delay = policy.initial_delay_seconds
        elif policy.policy_type == RetryPolicyType.EXPONENTIAL_BACKOFF:
            # Formula: min(initial * (backoff_factor ^ attempt) + jitter, max_delay)
            raw_delay = policy.initial_delay_seconds * (policy.backoff_factor ** (current_attempt - 1))
            jitter = random.uniform(0.0, 0.25 * raw_delay)
            delay = min(raw_delay + jitter, policy.max_delay_seconds)
        else:
            delay = policy.initial_delay_seconds

        logger.info(f"[RetryManager] Scheduling attempt {current_attempt + 1}/{policy.max_retries} after {delay:.2f}s delay.")
        return True, delay
