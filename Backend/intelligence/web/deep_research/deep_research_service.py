"""
Main WebDeepResearchService Orchestrator for J.A.R.V.I.S. I2.2 V5.
Delegates deep web research execution to ResearchController.
"""

from typing import Optional
from intelligence.web.deep_research.models import DeepResearchRequest, DeepResearchResponse
from intelligence.web.deep_research.research_controller import research_controller


class WebDeepResearchService:
    """Orchestrates V5 Deep Web Research & Source Discovery."""

    async def execute_deep_research(
        self,
        request: DeepResearchRequest
    ) -> DeepResearchResponse:
        """Executes bounded deep research request."""
        return await research_controller.execute_deep_research(request)


web_deep_research_service = WebDeepResearchService()
