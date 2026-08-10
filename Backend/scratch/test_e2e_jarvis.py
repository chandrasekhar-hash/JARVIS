import asyncio
from unittest.mock import patch, AsyncMock
from tools.router import handle_agent_chat
from intelligence.web.models import WebRetrievalStatus, GroundingStatus

async def test_e2e_flow():
    print("=== E2E JARVIS TEST 1: Full Page Retrieval Grounding ===")
    user_query = "What changed in the latest FastAPI release?"
    
    chunks = []
    async for chunk in handle_agent_chat(user_query, assistant_name="JARVIS", creator="cs"):
        chunks.append(chunk)

    response_text = "".join(chunks)
    print(f"JARVIS Response:\n{response_text}\n")

    print("=== E2E JARVIS TEST 2: Fallback to Search Snippet Grounding ===")
    with patch("intelligence.web.retrieval_service.web_retrieval_service.fetch_pages_parallel") as mock_fetch:
        # Mock retrieval failure
        mock_fetch.return_value = ([], {}, GroundingStatus.SEARCH_SNIPPET_FALLBACK)
        
        chunks_fb = []
        async for chunk in handle_agent_chat(user_query, assistant_name="JARVIS", creator="cs"):
            chunks_fb.append(chunk)

        response_fb = "".join(chunks_fb)
        print(f"Fallback Response:\n{response_fb}\n")

if __name__ == "__main__":
    asyncio.run(test_e2e_flow())
