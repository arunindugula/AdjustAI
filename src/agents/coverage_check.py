"""
Agent 2 — Coverage Check
=========================
Retrieves relevant policy clauses from the DocStore search API (Bedrock KB),
then assesses whether the incident is covered. Every coverage statement must
cite a retrieved clause_id — never from model memory (ADR-003).

Pattern: two-pass tool-calling loop.
  Pass 1: model decides what to search for → returns a tool call
  Pass 2: tool result injected → model returns CoverageCheckOutput
"""

from __future__ import annotations

import json
import os

import httpx
from openai import AsyncOpenAI

from schemas import CoverageCheckOutput, ClauseReference, DocumentIntakeOutput

_client = AsyncOpenAI()
_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_BASE   = os.getenv("API_BASE_URL", "http://localhost:3000")

_SYSTEM = """\
You are the Coverage Check agent for an insurance claims adjudication system.

Your responsibilities:
1. Call the search_policy_corpus tool with a precise, focused query to retrieve the most \
   relevant policy clauses for this incident type.
2. Using ONLY the retrieved clauses (never your training knowledge), determine:
   - Is this incident type covered?
   - Which specific clauses apply?
   - Are there any exclusions?
3. Populate cited_clauses with clause_id values taken directly from the tool response.
   cited_clauses MUST be non-empty — if no relevant clauses are found, use whatever was returned.
4. Set coverage_type to "collision", "comprehensive", or "none".

IMPORTANT: You must call search_policy_corpus before producing your output.\
"""

# Tool definition for the OpenAI API
_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_policy_corpus",
        "description": (
            "Search the AutoSure policy manual for coverage clauses relevant to this claim. "
            "Returns clause_id, clause_text, and relevance score for each result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "Natural language coverage question, e.g. 'collision deductible for at-fault accident'",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results (1-10, default 5)",
                    "default": 5,
                },
            },
            "required": ["query_text"],
        },
    },
}


async def run_coverage_check(
    claim:  dict,
    policy: dict,
    intake: DocumentIntakeOutput,
) -> CoverageCheckOutput:
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": _build_prompt(claim, policy, intake)},
    ]

    # Pass 1: model issues a tool call
    resp1 = await _client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        tools=[_SEARCH_TOOL],
        tool_choice={"type": "function", "function": {"name": "search_policy_corpus"}},
        temperature=0,
    )

    tool_call  = resp1.choices[0].message.tool_calls[0]
    tool_args  = json.loads(tool_call.function.arguments)
    tool_result = _search_policy_corpus(
        query_text=tool_args["query_text"],
        top_k=tool_args.get("top_k", 5),
    )

    # Pass 2: inject tool result, get structured CoverageCheckOutput
    messages.append(resp1.choices[0].message)   # assistant turn with tool_calls
    messages.append({
        "role":         "tool",
        "tool_call_id": tool_call.id,
        "content":      json.dumps(tool_result),
    })

    resp2 = await _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=messages,
        response_format=CoverageCheckOutput,
        temperature=0,
    )
    return resp2.choices[0].message.parsed


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

def _search_policy_corpus(query_text: str, top_k: int = 5) -> dict:
    r = httpx.get(
        f"{_BASE}/documents/search",
        params={"q": query_text, "top_k": min(max(top_k, 1), 10)},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(claim: dict, policy: dict, intake: DocumentIntakeOutput) -> str:
    facts = "\n".join(f"  - {f}" for f in intake.key_facts) or "  (none extracted)"
    pending = ", ".join(intake.documents_pending_ocr) or "none"

    return (
        f"CLAIM:\n"
        f"  Claim ID:       {claim.get('claim_id')}\n"
        f"  Incident type:  {claim.get('incident_type')}\n"
        f"  Incident date:  {claim.get('incident_date')}\n"
        f"  Description:    {claim.get('incident_description')}\n"
        f"  Damage:         {claim.get('damage_description')}\n"
        f"  Injuries:       {'Yes' if claim.get('injuries_reported') else 'No'}\n\n"
        f"POLICY:\n"
        f"  Policy ID:      {policy.get('policy_id')}\n"
        f"  Coverage type:  {policy.get('coverage_type')}\n"
        f"  Collision cov:  {policy.get('collision_coverage')}\n"
        f"  Comprehensive:  {policy.get('comprehensive_coverage')}\n\n"
        f"KEY FACTS FROM DOCUMENTS:\n{facts}\n"
        f"  (Pending OCR docs — not readable: {pending})\n\n"
        f"Search the policy corpus for relevant clauses, then produce your CoverageCheckOutput."
    )
