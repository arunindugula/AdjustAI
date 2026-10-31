"""
ClaimSense AI — MCP Server
==========================
Single MCP server exposing all three tool groups:
  CMS      — list_claims, get_claim, post_decision
  PAS      — get_policy
  DocStore — get_documents, search_policy_corpus

Transports
----------
  stdio (default)         — local Claude Code integration
                            python mcp-server/server.py

  streamable-http         — HTTP deployment (Lambda or local HTTP server)
                            MCP_TRANSPORT=streamable-http python mcp-server/server.py

  Lambda                  — deployed via SAM as MCPServerFunction in template.yaml
                            entry point: server.lambda_handler

Environment variables
---------------------
  API_BASE_URL    Base URL of the ClaimSense API
                  Default: http://localhost:3000 (SAM local)
                  On AWS: set to the API Gateway URL output from sam deploy
  MCP_ADJUSTER_ID Adjuster ID forwarded on CMS requests (default: mcp-agent)
  MCP_TRANSPORT   stdio | streamable-http (default: stdio)
  PORT            HTTP port when using streamable-http (default: 8080)
"""

import os
import sys

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "ClaimSense AI",
    instructions=(
        "Tools for the ClaimSense AI claims adjudication system. "
        "Workflow: (1) get_claim to read the claim, (2) get_policy with the "
        "claim's policy_id and incident_date to check coverage and in-force status, "
        "(3) get_documents to retrieve attached documents, "
        "(4) search_policy_corpus to retrieve coverage clauses — always cite "
        "clause_id in every coverage statement, never from memory, "
        "(5) post_decision to persist the confirmed verdict."
    ),
)

# ---------------------------------------------------------------------------
# Register tools
# ---------------------------------------------------------------------------

# Ensure tools/ is importable when running this file directly
sys.path.insert(0, os.path.dirname(__file__))

import tools.cms as _cms
import tools.pas as _pas
import tools.docstore as _docstore

_cms.register(mcp)
_pas.register(mcp)
_docstore.register(mcp)

# ---------------------------------------------------------------------------
# Lambda entry point (Streamable HTTP via Mangum)
#
# Mangum bridges the API Gateway proxy event format to ASGI.
# FastMCP 2.3+ exposes streamable_http_app() which returns a Starlette app.
# The handler is built once on the first cold start and reused on warm invocations.
# ---------------------------------------------------------------------------

_mangum_handler = None


def lambda_handler(event, context):
    global _mangum_handler
    if _mangum_handler is None:
        from mangum import Mangum
        _mangum_handler = Mangum(mcp.streamable_http_app(), lifespan="off")
    return _mangum_handler(event, context)


# ---------------------------------------------------------------------------
# Local entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
        )
    else:
        mcp.run()  # stdio — default for Claude Code
