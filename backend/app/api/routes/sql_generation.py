"""SQL generation API — mock implementation for UI prototyping."""

from fastapi import APIRouter

router = APIRouter()

_MOCK_SQL = """-- Semantic Bridge Generated SQL
-- Interview: Medical Enrollment Rate by Department
-- Confidence Score: 88/100
-- Generated: 2026-03-29T12:00:00Z

WITH eligible_employees AS (
    -- Employees who are benefits-eligible and currently active or on leave
    SELECT
        e.employee_id,
        e.department_id,
        e.client_id
    FROM hcm_analytics.employees AS e
    WHERE e.is_benefits_eligible = TRUE
        AND e.employment_status IN ('active', 'leave')
),

medical_enrollments AS (
    -- Employees with an active enrollment in a medical plan
    SELECT DISTINCT
        be.employee_id
    FROM hcm_analytics.benefit_enrollments AS be
    INNER JOIN hcm_analytics.benefit_plans AS bp
        ON be.plan_id = bp.plan_id
    WHERE be.enrollment_status = 'active'
        AND bp.plan_type = 'medical'
),

enrollment_by_department AS (
    SELECT
        d.department_name,
        COUNT(DISTINCT ee.employee_id) AS total_eligible,
        COUNT(DISTINCT me.employee_id) AS total_enrolled
    FROM eligible_employees AS ee
    INNER JOIN hcm_analytics.departments AS d
        ON ee.department_id = d.department_id
    LEFT JOIN medical_enrollments AS me
        ON ee.employee_id = me.employee_id
    WHERE ee.client_id = '{{ client_id }}'  -- Parameter: selected client
    GROUP BY d.department_name
)

SELECT
    department_name,
    total_eligible,
    total_enrolled,
    CASE
        WHEN total_eligible > 0
        THEN ROUND(total_enrolled::DECIMAL / total_eligible * 100, 2)
        ELSE 0
    END AS enrollment_rate_pct
FROM enrollment_by_department
ORDER BY enrollment_rate_pct DESC
"""


@router.post("/{interview_id}/sql")
async def generate_sql(interview_id: str):
    return {
        "interview_id": interview_id,
        "sql": _MOCK_SQL,
        "dialect": "snowflake",
        "lint_status": "passed",
        "lint_errors": [],
        "documentation": {
            "model_name": "medical_enrollment_rate_by_dept",
            "description": "Medical enrollment rate calculated as the percentage of benefits-eligible employees (active or on leave) who have an active medical plan enrollment, aggregated by department.",
            "grain": "One row per department",
            "source_tables": [
                "hcm_analytics.employees",
                "hcm_analytics.benefit_enrollments",
                "hcm_analytics.benefit_plans",
                "hcm_analytics.departments",
            ],
            "columns": [
                {"name": "department_name", "description": "Name of the department"},
                {"name": "total_eligible", "description": "Count of distinct benefits-eligible employees in the department"},
                {"name": "total_enrolled", "description": "Count of distinct employees with an active medical enrollment"},
                {"name": "enrollment_rate_pct", "description": "Enrollment rate as a percentage (enrolled / eligible × 100)"},
            ],
            "filters_applied": [
                "employees.is_benefits_eligible = TRUE",
                "employees.employment_status IN ('active', 'leave')",
                "benefit_plans.plan_type = 'medical'",
                "benefit_enrollments.enrollment_status = 'active'",
                "employees.client_id = <selected client>",
            ],
            "interview_id": interview_id,
            "confidence_score": 88,
        },
    }
