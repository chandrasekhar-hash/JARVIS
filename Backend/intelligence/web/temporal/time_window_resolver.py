"""
Time Window Resolver for J.A.R.V.I.S. I2.2 V4.
Resolves relative date expressions into normalized UTC TemporalWindow instances.
Respects timezone resolution precedence without defaulting relative queries to UTC.
"""

import datetime

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore

from typing import Optional
from intelligence.web.temporal.models import TemporalWindow, TemporalIntent


class TimeWindowResolver:
    """Resolves relative date expressions into UTC TemporalWindow instances."""

    def resolve_time_window(
        self,
        query: str,
        intent: TemporalIntent,
        request_timezone: Optional[str] = None,
        session_timezone: Optional[str] = None
    ) -> TemporalWindow:
        """
        Resolves query expression to normalized UTC ISO-8601 start/end timestamps.
        Resolution precedence: Request TZ -> Session TZ -> None.
        If timezone is unknown and affects relative dates, sets resolution_status = UNCERTAIN_TIMEZONE.
        """
        # 1. Determine active user timezone
        resolved_tz_str = request_timezone or session_timezone or None
        is_tz_known = resolved_tz_str is not None

        res_status = "RESOLVED"
        if not is_tz_known and intent in [TemporalIntent.TODAY, TemporalIntent.YESTERDAY, TemporalIntent.THIS_WEEK]:
            res_status = "UNCERTAIN_TIMEZONE"

        # Validate timezone string
        tz_obj = datetime.timezone.utc
        if resolved_tz_str:
            try:
                tz_obj = zoneinfo.ZoneInfo(resolved_tz_str)
            except Exception:
                resolved_tz_str = None
                res_status = "INVALID_TIMEZONE"
                tz_obj = datetime.timezone.utc

        now_local = datetime.datetime.now(tz_obj)
        now_utc = now_local.astimezone(datetime.timezone.utc)

        start_utc: Optional[datetime.datetime] = None
        end_utc: Optional[datetime.datetime] = now_utc

        if intent == TemporalIntent.TODAY:
            # Beginning of local day in target timezone
            start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            start_utc = start_local.astimezone(datetime.timezone.utc)

        elif intent == TemporalIntent.YESTERDAY:
            yesterday_local = now_local - datetime.timedelta(days=1)
            start_local = yesterday_local.replace(hour=0, minute=0, second=0, microsecond=0)
            end_local = yesterday_local.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_utc = start_local.astimezone(datetime.timezone.utc)
            end_utc = end_local.astimezone(datetime.timezone.utc)

        elif intent == TemporalIntent.LAST_24_HOURS:
            start_utc = now_utc - datetime.timedelta(hours=24)

        elif intent == TemporalIntent.THIS_WEEK:
            start_utc = now_utc - datetime.timedelta(days=7)

        elif intent == TemporalIntent.THIS_MONTH:
            start_utc = now_utc - datetime.timedelta(days=30)

        elif intent in [TemporalIntent.LATEST, TemporalIntent.BREAKING_NEWS, TemporalIntent.NEWS_SUMMARY]:
            start_utc = now_utc - datetime.timedelta(days=3)

        return TemporalWindow(
            start_time=start_utc.isoformat() if start_utc else None,
            end_time=end_utc.isoformat() if end_utc else None,
            user_timezone=resolved_tz_str,
            source_expression=query,
            is_relative=True,
            resolution_status=res_status
        )


time_window_resolver = TimeWindowResolver()
