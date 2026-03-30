"""Interview API routes — real LLM-powered interview flow."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_service import chat_completion

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory store for prototype ──
_interviews: Dict[str, dict] = {}


class StartInterviewRequest(BaseModel):
    title: str
    description: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str


class InterviewSummary(BaseModel):
    interview_id: str
    title: str
    status: str
    confidence_score: float
    created_at: str
    turn_count: int


def _compute_score(factors: dict) -> float:
    weights = {
        "entity_resolution": 0.35,
        "temporal_completeness": 0.20,
        "grain_clarity": 0.20,
        "join_validity": 0.15,
        "filter_completeness": 0.10,
    }
    score = sum(factors.get(k, 0) * w for k, w in weights.items()) * 100
    return round(score, 1)


def _build_conversation_messages(interview: dict) -> List[Dict[str, str]]:
    """Convert stored turns into OpenAI message format (text-only)."""
    messages = []
    for turn in interview["turns"]:
        messages.append({
            "role": turn["role"],
            "content": turn["content"],
        })
    return messages


@router.post("", response_model=InterviewSummary)
async def start_interview(req: StartInterviewRequest):
    interview_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    interview = {
        "interview_id": interview_id,
        "title": req.title,
        "description": req.description,
        "status": "in_progress",
        "confidence_score": 0.0,
        "created_at": now,
        "turns": [],
        "entities": [],
        "confidence_factors": {},
    }
    _interviews[interview_id] = interview
    return InterviewSummary(
        interview_id=interview_id,
        title=req.title,
        status="in_progress",
        confidence_score=0.0,
        created_at=now,
        turn_count=0,
    )


@router.get("", response_model=List[InterviewSummary])
async def list_interviews():
    return [
        InterviewSummary(
            interview_id=iv["interview_id"],
            title=iv["title"],
            status=iv["status"],
            confidence_score=iv["confidence_score"],
            created_at=iv["created_at"],
            turn_count=len(iv["turns"]),
        )
        for iv in _interviews.values()
    ]


@router.get("/{interview_id}")
async def get_interview(interview_id: str):
    iv = _interviews.get(interview_id)
    if not iv:
        return {"error": "Not found"}
    return iv


@router.post("/{interview_id}/messages")
async def send_message(interview_id: str, req: SendMessageRequest):
    iv = _interviews.get(interview_id)
    if not iv:
        return {"error": "Not found"}

    # Record the user turn
    user_turn = {
        "role": "user",
        "content": req.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    iv["turns"].append(user_turn)

    # Build conversation history and call GPT-4o
    conversation = _build_conversation_messages(iv)
    llm_result = await chat_completion(conversation)

    assistant_turn = {
        "role": "assistant",
        "content": llm_result["response_text"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extracted_entities": llm_result["extracted_entities"],
        "clarification_needed": llm_result["clarification_needed"],
        "confidence_factors": llm_result["confidence_factors"],
    }

    iv["turns"].append(assistant_turn)
    iv["entities"] = llm_result["extracted_entities"]
    iv["confidence_factors"] = llm_result["confidence_factors"]
    iv["confidence_score"] = _compute_score(llm_result["confidence_factors"])

    if iv["confidence_score"] >= 80:
        iv["status"] = "ready"
    elif iv["confidence_score"] >= 60:
        iv["status"] = "needs_review"

    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "confidence_score": iv["confidence_score"],
        "confidence_factors": iv["confidence_factors"],
        "entities": iv["entities"],
        "status": iv["status"],
    }


@router.get("/{interview_id}/flow-diagram")
async def get_flow_diagram(interview_id: str):
    """Return a mock logic flow diagram as a DAG."""
    iv = _interviews.get(interview_id)
    if not iv:
        return {"error": "Not found"}

    return {
        "interview_id": interview_id,
        "nodes": [
            {"id": "employees", "type": "source", "label": "employees", "schema": "hcm_analytics"},
            {"id": "benefit_enrollments", "type": "source", "label": "benefit_enrollments", "schema": "hcm_analytics"},
            {"id": "benefit_plans", "type": "source", "label": "benefit_plans", "schema": "hcm_analytics"},
            {"id": "departments", "type": "source", "label": "departments", "schema": "hcm_analytics"},
            {"id": "filter_eligible", "type": "filter", "label": "is_benefits_eligible = TRUE\nemployment_status IN ('active','leave')"},
            {"id": "filter_medical", "type": "filter", "label": "plan_type = 'medical'\nenrollment_status = 'active'"},
            {"id": "join_emp_enroll", "type": "join", "label": "JOIN on employee_id"},
            {"id": "join_enroll_plan", "type": "join", "label": "JOIN on plan_id"},
            {"id": "join_emp_dept", "type": "join", "label": "JOIN on department_id"},
            {"id": "aggregate", "type": "aggregation", "label": "COUNT DISTINCT employee_id\nGROUP BY department_name"},
            {"id": "output", "type": "output", "label": "medical_enrollment_rate_by_dept\nGrain: 1 row per department"},
        ],
        "edges": [
            {"source": "employees", "target": "filter_eligible"},
            {"source": "benefit_enrollments", "target": "join_enroll_plan"},
            {"source": "benefit_plans", "target": "filter_medical"},
            {"source": "filter_medical", "target": "join_enroll_plan"},
            {"source": "filter_eligible", "target": "join_emp_enroll"},
            {"source": "join_enroll_plan", "target": "join_emp_enroll"},
            {"source": "join_emp_enroll", "target": "join_emp_dept"},
            {"source": "departments", "target": "join_emp_dept"},
            {"source": "join_emp_dept", "target": "aggregate"},
            {"source": "aggregate", "target": "output"},
        ],
    }
