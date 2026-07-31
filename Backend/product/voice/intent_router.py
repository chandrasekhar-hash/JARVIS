"""
JARVIS Product 1.9 - Voice Intent Router.
Classifies recognized transcripts into action routes (TOOL_EXECUTION, KNOWLEDGE_RAG, AUTOMATION_WORKFLOW, CONVERSATIONAL_CHAT) and dispatches via P1.5.
"""

import logging
from typing import Tuple, Dict, Any, Optional
from .models import IntentCategory
from ..tools import tool_execution_manager_instance

logger = logging.getLogger(__name__)


class IntentRouter:
    def route_transcript(self, transcript: str, owner_id: str) -> Tuple[IntentCategory, Optional[str], Dict[str, Any], str]:
        text = transcript.lower().strip()

        # 1. Check for Tool Execution keywords (e.g., "slack", "github", "email", "sync")
        if "slack" in text or "email" in text or "github" in text or "integration" in text or "tool" in text:
            logger.info(f"[IntentRouter] Classifying transcript as TOOL_EXECUTION.")
            # Dispatch via P1.5 Tool Execution Engine
            return IntentCategory.TOOL_EXECUTION, "integration_list_connectors", {"owner_id": owner_id}, "Listed connected workspace platforms."

        # 2. Check for Knowledge RAG queries (e.g., "search", "document", "knowledge", "find")
        if "search" in text or "document" in text or "knowledge" in text or "what is" in text:
            logger.info(f"[IntentRouter] Classifying transcript as KNOWLEDGE_RAG.")
            return IntentCategory.KNOWLEDGE_RAG, "knowledge_search", {"query": transcript, "owner_id": owner_id}, f"Searched knowledge base for '{transcript}'."

        # 3. Check for Automation Workflows (e.g., "workflow", "trigger", "automation")
        if "workflow" in text or "automation" in text or "trigger" in text:
            logger.info(f"[IntentRouter] Classifying transcript as AUTOMATION_WORKFLOW.")
            return IntentCategory.AUTOMATION_WORKFLOW, "automation_list_workflows", {"owner_id": owner_id}, "Retrieved active automation workflows."

        # 4. Default to Conversational Chat
        logger.info(f"[IntentRouter] Classifying transcript as CONVERSATIONAL_CHAT.")
        return IntentCategory.CONVERSATIONAL_CHAT, None, {}, f"Hello! I am JARVIS. You said: '{transcript}'."
