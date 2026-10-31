"""
CMS tools — Claims Management System
Exposes list_claims, get_claim, and post_decision to MCP clients.
"""

import hashlib
import os

import httpx
from fastmcp import FastMCP

_BASE = os.getenv("API_BASE_URL", "http://localhost:3000")
_ADJUSTER = os.getenv("MCP_ADJUSTER_ID", "mcp-agent")


def _client() -> httpx.Client:
    return httpx.Client(base_url=_BASE, timeout=30.0)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_claims() -> dict:
        """List all claims in the system. Use this to get a claim_id before calling get_claim."""
        with _client() as c:
            r = c.get("/claims", headers={"X-Adjuster-Id": _ADJUSTER})
            r.raise_for_status()
            return r.json()

    @mcp.tool()
    def get_claim(claim_id: str) -> dict:
        """
        Get a single claim record by claim_id (e.g. CLM-2024-1800).
        Returns the full claim record including any existing confirmed decision.
        """
        with _client() as c:
            r = c.get(f"/claims/{claim_id}", headers={"X-Adjuster-Id": _ADJUSTER})
            r.raise_for_status()
            return r.json()

    @mcp.tool()
    def post_decision(
        claim_id: str,
        adjuster_id: str,
        verdict: str,
        reasoning_summary: str,
        reasoning_chain: list[str],
        citations: list[str],
        deterministic_checks_passed: bool,
        model_generated: bool,
        pipeline_run_id: str,
    ) -> dict:
        """
        Persist a confirmed adjudication decision for a claim.

        verdict must be one of: Approve | Deny | Refer-Fraud | Refer-Adjuster
        reasoning_chain: ordered list of reasoning steps (strings)
        citations: list of clause_id strings retrieved from search_policy_corpus
        deterministic_checks_passed: True if pre-checks ran without a hard deny
        model_generated: True for agent verdicts, False for deterministic denies
        pipeline_run_id: unique identifier for the pipeline run

        The idempotency key is computed automatically — duplicate POSTs return
        the original record (409) rather than writing again.
        """
        if verdict not in ("Approve", "Deny", "Refer-Fraud", "Refer-Adjuster"):
            raise ValueError(f"Invalid verdict '{verdict}'. Must be one of: Approve | Deny | Refer-Fraud | Refer-Adjuster")

        idempotency_key = hashlib.sha256(
            f"{claim_id}:{adjuster_id}:{verdict}".encode()
        ).hexdigest()

        body = {
            "adjuster_id":                 adjuster_id,
            "verdict":                     verdict,
            "reasoning_summary":           reasoning_summary,
            "reasoning_chain":             reasoning_chain,
            "citations":                   citations,
            "deterministic_checks_passed": deterministic_checks_passed,
            "model_generated":             model_generated,
            "pipeline_run_id":             pipeline_run_id,
        }
        with _client() as c:
            r = c.post(
                f"/claims/{claim_id}/decision",
                json=body,
                headers={
                    "X-Adjuster-Id":    adjuster_id,
                    "Idempotency-Key":  idempotency_key,
                },
            )
            if r.status_code not in (201, 409):
                r.raise_for_status()
            return r.json()
