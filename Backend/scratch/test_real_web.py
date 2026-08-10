import asyncio
from intelligence.web.models import WebPageRequest
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.search_service import web_search_service

async def run_real_web_tests():
    print("=== REAL-WEB TEST 1: FastAPI Authentication / Release Docs ===")
    req1 = WebPageRequest(url="https://fastapi.tiangolo.com/tutorial/security/", query="OAuth2 authentication")
    res1 = await web_retrieval_service.fetch_page(req1)
    print(f"Status: {res1.document.retrieval_status.value if res1.document else res1.error}")
    if res1.document and res1.document.blocks:
        print(f"Title: {res1.document.metadata.title}")
        print(f"Extracted blocks: {len(res1.document.blocks)}")
        print(f"Evidence chunks: {len(res1.document.evidence_chunks)}")
        if res1.document.evidence_chunks:
            print(f"Sample Chunk Text:\n{res1.document.evidence_chunks[0].text[:300]}...")

    print("\n=== REAL-WEB TEST 2: Python.org ===")
    req2 = WebPageRequest(url="https://www.python.org/downloads/", query="latest python release")
    res2 = await web_retrieval_service.fetch_page(req2)
    print(f"Status: {res2.document.retrieval_status.value if res2.document else res2.error}")
    if res2.document:
        print(f"Title: {res2.document.metadata.title}")
        print(f"Content length: {res2.document.content_length} chars")

    print("\n=== REAL-WEB TEST 3: Blocked/Invalid Page Fallback ===")
    req3 = WebPageRequest(url="http://127.0.0.1/admin", query="internal secret")
    res3 = await web_retrieval_service.fetch_page(req3)
    print(f"Status (Expected SSRF_BLOCKED): {res3.document.retrieval_status.value if res3.document else res3.error}")

if __name__ == "__main__":
    asyncio.run(run_real_web_tests())
