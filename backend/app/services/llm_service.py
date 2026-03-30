"""LLM service — handles GPT-4o calls for the Semantic Bridge interview flow."""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


# ── Schema context (loaded once, injected into system prompt) ──

def _build_schema_summary() -> str:
    """Build a compact text representation of the HCM schema for the system prompt."""
    from app.api.routes.schema import _MOCK_SCHEMA

    lines = [f"Schema: {_MOCK_SCHEMA['schema_name']}", ""]
    for table in _MOCK_SCHEMA["tables"]:
        cols = []
        for c in table["columns"]:
            flags = []
            if c["is_pk"]:
                flags.append("PK")
            if c["is_pii"]:
                flags.append("PII")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            cols.append(f"    {c['name']} {c['type']}{flag_str} -- {c['description']}")

        fk_lines = []
        for fk in table.get("foreign_keys", []):
            fk_lines.append(f"    FK: {fk['column']} -> {fk['references']}")

        lines.append(f"TABLE {table['table_name']} -- {table['description']}")
        lines.extend(cols)
        if fk_lines:
            lines.extend(fk_lines)
        lines.append("")

    return "\n".join(lines)


_SCHEMA_SUMMARY: Optional[str] = None


def _get_schema_summary() -> str:
    global _SCHEMA_SUMMARY
    if _SCHEMA_SUMMARY is None:
        _SCHEMA_SUMMARY = _build_schema_summary()
    return _SCHEMA_SUMMARY


# ── System prompt ──

SYSTEM_PROMPT = """\
You are **Semantic Bridge**, an AI assistant that helps domain experts translate \
business metric requests into precise data transformation specifications.

## Your Role
You conduct structured interviews with domain experts (e.g. Benefits analysts, \
HR data leads) to understand what data metric or report they need. You ask \
clarifying questions until every ambiguity is resolved, then produce a structured \
specification that a data engineer can implement.

## Domain Context
You are working with an HCM (Human Capital Management) platform in the **Benefits** \
domain. You have access to metadata only — no actual client row data. The schema \
is multi-tenant: each client (company) has different plans, eligibility rules, \
regions, and salary bands.

## Available Schema
{schema}

## Interview Rules
1. **Start by understanding the business question** — what metric, report, or \
   dataset does the user need?
2. **Probe for ambiguities** — resolve every unclear term by mapping it to specific \
   schema columns. Common ambiguities in Benefits:
   - "enrolled" — active enrollments only, or including waived/pending?
   - "eligible" — using `is_benefits_eligible` flag, or derived from eligibility rules?
   - "plan" — all plan types, or specific types (medical, dental, etc.)?
   - Time period — current snapshot, specific plan year, or historical trend?
   - Grain — per employee, per department, per region, per client?
   - Client scope — single client, or cross-client comparison?
3. **Map business terms to schema** — explicitly call out which table.column you're  \
   mapping each term to. Use format: `table_name.column_name`
4. **Track confidence** — after each exchange, assess your confidence across these \
   factors (0.0 to 1.0):
   - `entity_resolution`: Have all business terms been mapped to specific columns?
   - `temporal_completeness`: Is the time scope fully defined?
   - `grain_clarity`: Is the output grain (what each row represents) clear?
   - `join_validity`: Are all required table joins identified and valid?
   - `filter_completeness`: Are all WHERE conditions specified?
5. **Never assume** — if something is ambiguous, ask. One question at a time is ideal, \
   but you can batch 2-3 related questions.
6. **Be conversational but precise** — use markdown formatting for clarity.
7. **PII columns are metadata-only** — note them but don't use them in metrics.

## Response Format
You MUST respond with valid JSON in exactly this structure (no markdown code fences, \
just raw JSON):

{{
  "response_text": "Your conversational response in markdown to the user",
  "extracted_entities": [
    {{
      "term": "the business term used by the user",
      "candidates": ["schema.table.column", "schema.table.column"],
      "resolved": true or false,
      "selected": "schema.table.column (only if resolved)",
      "filter_value": "specific value or null"
    }}
  ],
  "clarification_needed": ["list of unresolved topics as short identifiers"],
  "confidence_factors": {{
    "entity_resolution": 0.0,
    "temporal_completeness": 0.0,
    "grain_clarity": 0.0,
    "join_validity": 0.0,
    "filter_completeness": 0.0
  }}
}}

IMPORTANT: Return ONLY the JSON object. No markdown code fences, no extra text before \
or after the JSON.
"""


def build_system_message() -> str:
    """Return the full system prompt with schema injected."""
    return SYSTEM_PROMPT.format(schema=_get_schema_summary())


async def chat_completion(
    conversation_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Send the interview conversation to GPT-4o and parse the structured response.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": "..."}
                              messages representing the full conversation so far.

    Returns:
        Parsed dict with response_text, extracted_entities, clarification_needed,
        and confidence_factors.
    """
    client = _get_client()

    messages = [{"role": "system", "content": build_system_message()}]
    messages.extend(conversation_history)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content
    logger.info("LLM raw response length: %d", len(raw_content))

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON response: %s", raw_content[:500])
        parsed = {
            "response_text": raw_content,
            "extracted_entities": [],
            "clarification_needed": [],
            "confidence_factors": {
                "entity_resolution": 0.0,
                "temporal_completeness": 0.0,
                "grain_clarity": 0.0,
                "join_validity": 0.0,
                "filter_completeness": 0.0,
            },
        }

    # Ensure all required keys exist
    parsed.setdefault("response_text", "")
    parsed.setdefault("extracted_entities", [])
    parsed.setdefault("clarification_needed", [])
    parsed.setdefault("confidence_factors", {
        "entity_resolution": 0.0,
        "temporal_completeness": 0.0,
        "grain_clarity": 0.0,
        "join_validity": 0.0,
        "filter_completeness": 0.0,
    })

    return parsed
