"""
PAS tools — Policy Administration System
Exposes get_policy to MCP clients.
"""

import os

import httpx
from fastmcp import FastMCP

_BASE = os.getenv("API_BASE_URL", "http://localhost:3000")


def _client() -> httpx.Client:
    return httpx.Client(base_url=_BASE, timeout=30.0)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_policy(policy_id: str, incident_date: str = "") -> dict:
        """
        Get a policy record by policy_id (e.g. POL-TXA-88339).

        Pass incident_date (YYYY-MM-DD) to get two computed deterministic flags:
          in_force       — whether the policy was active on that date
          liability_only — True when coverage_type is "Liability Only"
                           (triggers automatic deny before agents run)

        These flags are computed by the server — never by the model (ADR-005).
        """
        params = {}
        if incident_date:
            params["incident_date"] = incident_date
        with _client() as c:
            r = c.get(f"/policies/{policy_id}", params=params)
            r.raise_for_status()
            return r.json()
