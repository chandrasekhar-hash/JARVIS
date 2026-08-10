"""
Story Clusterer for J.A.R.V.I.S. I2.2 V4.
Clusters news reports describing the same underlying event to prevent syndicated inflation.
"""

from typing import List, Dict
from intelligence.web.research.models import ResearchSource
from intelligence.web.temporal.models import StoryCluster, NewsEvent


class StoryClusterer:
    """Clusters news events into StoryCluster instances."""

    def cluster_events(
        self,
        events: List[NewsEvent],
        sources: List[ResearchSource],
        primary_source: Optional[ResearchSource] = None
    ) -> List[StoryCluster]:
        """
        Clusters events by sub-topic / title similarity.
        Prevents 10 syndicated news articles from inflating into 10 fake developments.
        """
        if not events:
            return []

        clusters: List[StoryCluster] = []
        source_map = {s.source_id: s for s in sources}
        primary_src_id = primary_source.source_id if primary_source else None

        # Group events into clusters
        grouped: Dict[str, List[NewsEvent]] = {}
        for ev in events:
            topic = ev.title.split(":")[0] if ":" in ev.title else "General Event"
            grouped.setdefault(topic, []).append(ev)

        for idx, (topic, ev_list) in enumerate(grouped.items()):
            member_srcs = set()
            for ev in ev_list:
                member_srcs.update(ev.source_ids)

            cluster = StoryCluster(
                cluster_id=f"cluster_{idx + 1}",
                topic_title=topic,
                primary_source_id=primary_src_id,
                member_source_ids=list(member_srcs),
                events=ev_list,
                is_old_news_resurfacing=False
            )
            clusters.append(cluster)

        return clusters


story_clusterer = StoryClusterer()
