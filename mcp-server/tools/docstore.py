"""
DocStore tools — Document Store and Bedrock policy search
Exposes get_documents and search_policy_corpus to MCP clients.
"""

import os

import httpx
from fastmcp import FastMCP

_BASE = os.getenv("API_BASE_URL", "http://localhost:3000")


def _client() -> httpx.Client:
    return httpx.Client(base_url=_BASE, timeout=30.0)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_documents(claim_id: str) -> dict:
        """
        List all documents attached to a claim.
        Each document includes ocr_status (Completed | Pending) and content_text.
        Documents with ocr_status=Pending have not been OCR-processed yet
        and should be flagged rather than read.
        """
        with _client() as c:
            r = c.get("/documents", params={"claim_id": claim_id})
            r.raise_for_status()
            return r.json()

    @mcp.tool()
    def search_policy_corpus(query_text: str, top_k: int = 5) -> dict:
        """
        Search the AutoSure policy manual (Bedrock Knowledge Base) for coverage clauses.

        Returns the top_k most relevant clause chunks. Each result includes:
          clause_id    — e.g. "CLS-COLL-001" — MUST be cited in every coverage statement
          clause_text  — the retrieved passage from the policy manual
          score        — relevance score 0.0–1.0

        IMPORTANT: Every coverage determination must cite a clause_id from this
        response. Never state coverage from memory without a retrieved clause (ADR-003).

        top_k: number of results to return (1–10, default 5)
        """
        with _client() as c:
            r = c.get(
                "/documents/search",
                params={"q": query_text, "top_k": min(max(top_k, 1), 10)},
            )
            r.raise_for_status()
            return r.json()
