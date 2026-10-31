"""
Agent 1 — Document Intake
=========================
Normalises raw claim documents, summarises each one, and extracts key facts.
Documents with ocr_status=Pending are flagged — their content is not read.

Input:  claim dict + list of document dicts (from DocStore Lambda)
Output: DocumentIntakeOutput (structured, validated by OpenAI)
"""

from __future__ import annotations

import json
import os

from openai import AsyncOpenAI

from schemas import DocumentIntakeOutput

_client = AsyncOpenAI()
_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_SYSTEM = """\
You are the Document Intake agent for an insurance claims adjudication system.

Your responsibilities:
- Summarise each document in one sentence based on its type, description, and content_text.
- If ocr_status is "Pending", set status to "pending_ocr" and leave content_summary blank — \
  do not invent content for documents that have not been processed.
- Extract a list of key_facts from completed documents: specific facts (dates, amounts, \
  descriptions, witness names, police report numbers) that are directly relevant to this claim.
- Write intake_notes: a 2-3 sentence overview of the document set quality and any gaps.

Be factual. Do not assess coverage. Do not recommend approve or deny.\
"""


async def run_document_intake(
    claim:     dict,
    documents: list[dict],
) -> DocumentIntakeOutput:
    user_msg = _build_prompt(claim, documents)

    result = await _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system",  "content": _SYSTEM},
            {"role": "user",    "content": user_msg},
        ],
        response_format=DocumentIntakeOutput,
        temperature=0,
    )
    return result.choices[0].message.parsed


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(claim: dict, documents: list[dict]) -> str:
    claim_summary = (
        f"Claim ID:      {claim.get('claim_id')}\n"
        f"Incident date: {claim.get('incident_date')}\n"
        f"Incident type: {claim.get('incident_type')}\n"
        f"Description:   {claim.get('incident_description')}\n"
        f"Damage:        {claim.get('damage_description')}\n"
        f"Injuries:      {'Yes' if claim.get('injuries_reported') else 'No'}\n"
        f"Police report: {'Yes' if claim.get('police_report_filed') else 'No'}"
    )

    doc_lines = []
    for d in documents:
        doc_lines.append(
            f"  - {d.get('document_id')} | {d.get('document_type')} | "
            f"OCR: {d.get('ocr_status')} | {d.get('description')}\n"
            f"    content_text: {str(d.get('content_text', ''))[:400] or '(empty)'}"
        )

    return (
        f"CLAIM:\n{claim_summary}\n\n"
        f"DOCUMENTS ({len(documents)} total):\n" + "\n".join(doc_lines)
    )
