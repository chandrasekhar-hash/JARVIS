import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Tuple, Optional
from autonomous.scheduler_models import ScheduleTrigger, JobType

WEEKDAYS_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6
}

def parse_natural_language_schedule(expression: str) -> ScheduleTrigger:
    """
    Parses natural language schedule expressions into a ScheduleTrigger object.
    Supports expressions like:
      - "Every 30 minutes", "Every 2 hours"
      - "Every morning at 8", "Every day at 08:00"
      - "Every weekday"
      - "Every Sunday", "Every Friday at 6 PM"
      - "First day of every month"
      - "Run once in 10 minutes"
    """
    text = expression.strip().lower()
    
    # 1. Interval matching: "every X minutes / hours / seconds"
    m_int = re.search(r'every\s+(\d+)\s+(second|sec|minute|min|hour|hr|day)s?', text)
    if m_int:
        val = int(m_int.group(1))
        unit = m_int.group(2)
        multiplier = 1
        if unit in ["minute", "min"]:
            multiplier = 60
        elif unit in ["hour", "hr"]:
            multiplier = 3600
        elif unit in ["day"]:
            multiplier = 86400
        interval = val * multiplier
        return ScheduleTrigger(
            job_type=JobType.INTERVAL,
            expression=expression,
            interval_seconds=interval
        )
        
    # 2. Daily time matching: "every morning at 8", "every day at 08:00", "daily at 18:30"
    m_daily_time = re.search(r'(every\s+(morning|day|evening|night)|daily)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if m_daily_time:
        hr = int(m_daily_time.group(3))
        mn = int(m_daily_time.group(4)) if m_daily_time.group(4) else 0
        ampm = m_daily_time.group(5)
        if ampm == "pm" and hr < 12:
            hr += 12
        elif ampm == "am" and hr == 12:
            hr = 0
        time_str = f"{hr:02d}:{mn:02d}"
        return ScheduleTrigger(
            job_type=JobType.DAILY,
            expression=expression,
            time_of_day=time_str
        )
        
    # 3. Simple daily matching: "every day", "daily"
    if text in ["every day", "daily", "every morning"]:
        return ScheduleTrigger(
            job_type=JobType.DAILY,
            expression=expression,
            time_of_day="08:00"
        )
        
    # 4. Weekday matching: "every weekday"
    if "every weekday" in text or "weekdays" in text:
        return ScheduleTrigger(
            job_type=JobType.WEEKLY,
            expression=expression,
            day_of_week=0, # Defaults Mon-Fri in logic
            time_of_day="09:00"
        )
        
    # 5. Day of week matching: "every Sunday", "every Friday at 6 PM"
    m_weekly = re.search(r'every\s+(monday|mon|tuesday|tue|wednesday|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?', text)
    if m_weekly:
        day_str = m_weekly.group(1)
        dow = WEEKDAYS_MAP.get(day_str, 0)
        time_str = "08:00"
        if m_weekly.group(2):
            hr = int(m_weekly.group(2))
            mn = int(m_weekly.group(3)) if m_weekly.group(3) else 0
            ampm = m_weekly.group(4)
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            time_str = f"{hr:02d}:{mn:02d}"
        return ScheduleTrigger(
            job_type=JobType.WEEKLY,
            expression=expression,
            day_of_week=dow,
            time_of_day=time_str
        )
        
    # 6. Monthly matching: "first day of every month", "monthly"
    if "first day of" in text or "monthly" in text or "every month" in text:
        return ScheduleTrigger(
            job_type=JobType.MONTHLY,
            expression=expression,
            day_of_month=1,
            time_of_day="08:00"
        )

    # Fallback default: Interval 3600 seconds
    return ScheduleTrigger(
        job_type=JobType.INTERVAL,
        expression=expression,
        interval_seconds=3600
    )


def compute_next_run(trigger: ScheduleTrigger, base_time: Optional[float] = None) -> float:
    """
    Computes the next epoch execution timestamp for a given ScheduleTrigger.
    """
    now = datetime.fromtimestamp(base_time or time.time())
    
    if trigger.job_type == JobType.ONE_TIME:
        if trigger.run_at and trigger.run_at > now.timestamp():
            return trigger.run_at
        return now.timestamp() + (trigger.interval_seconds or 60)
        
    if trigger.job_type == JobType.INTERVAL:
        sec = trigger.interval_seconds or 3600
        return now.timestamp() + sec
        
    # Parse time_of_day "HH:MM"
    hr, mn = 8, 0
    if trigger.time_of_day:
        parts = trigger.time_of_day.split(":")
        if len(parts) >= 2:
            try:
                hr, mn = int(parts[0]), int(parts[1])
            except ValueError:
                pass
                
    target_time = dt_time(hour=hr, minute=mn)
    
    if trigger.job_type == JobType.DAILY:
        candidate = datetime.combine(now.date(), target_time)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.timestamp()
        
    if trigger.job_type == JobType.WEEKLY:
        target_dow = trigger.day_of_week if trigger.day_of_week is not None else 0
        days_ahead = target_dow - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and datetime.combine(now.date(), target_time) <= now):
            days_ahead += 7
        candidate = datetime.combine(now.date() + timedelta(days=days_ahead), target_time)
        return candidate.timestamp()
        
    if trigger.job_type == JobType.MONTHLY:
        target_dom = trigger.day_of_month or 1
        year, month = now.year, now.month
        # Try current month first
        try:
            candidate = datetime(year, month, target_dom, hr, mn)
        except ValueError:
            candidate = datetime(year, month, 28, hr, mn)
            
        if candidate <= now:
            # Move to next month
            month += 1
            if month > 12:
                month = 1
                year += 1
            try:
                candidate = datetime(year, month, target_dom, hr, mn)
            except ValueError:
                candidate = datetime(year, month, 28, hr, mn)
        return candidate.timestamp()
        
    return now.timestamp() + 3600
