"""
Update Detector & Old-News Resurfacing Detector for J.A.R.V.I.S. I2.2 V4.
Classifies story update categories and detects old news resurfacing today.
"""

import datetime
from typing import List, Tuple
from intelligence.web.temporal.models import (
    StoryCluster,
    NewsEvent,
    UpdateCategory,
    TemporalWindow
)


class UpdateDetector:
    """Classifies update categories and detects old-news resurfacing."""

    def classify_and_detect_resurfacing(
        self,
        clusters: List[StoryCluster],
        window: TemporalWindow
    ) -> List[StoryCluster]:
        """
        Classifies story update categories and tags old news resurfacing.
        If publication date precedes target window, tags is_old_news_resurfacing = True.
        """
        for cluster in clusters:
            for ev in cluster.events:
                # Classify update category
                desc_lower = ev.description.lower()
                if "correction" in desc_lower or "update:" in desc_lower:
                    ev.update_category = UpdateCategory.CORRECTION
                elif "confirm" in desc_lower or "official" in desc_lower:
                    ev.update_category = UpdateCategory.OFFICIAL_CONFIRMATION
                elif "detail" in desc_lower or "added" in desc_lower:
                    ev.update_category = UpdateCategory.NEW_DETAIL
                else:
                    ev.update_category = UpdateCategory.NEW_EVENT

                # Detect old-news resurfacing
                if ev.first_published_at and window.start_time:
                    try:
                        pub_dt = datetime.datetime.fromisoformat(ev.first_published_at.replace("Z", "+00:00"))
                        start_dt = datetime.datetime.fromisoformat(window.start_time.replace("Z", "+00:00"))
                        if pub_dt < start_dt - datetime.timedelta(days=30):
                            cluster.is_old_news_resurfacing = True
                            cluster.resurfaced_original_date = ev.first_published_at
                    except Exception:
                        pass

        return clusters


update_detector = UpdateDetector()
