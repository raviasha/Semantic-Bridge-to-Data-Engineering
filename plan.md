# Plan: Semantic Bridge Prototype

## TL;DR
Build a working prototype that proves the core value loop — AI interviews a domain expert, grounds answers against real schema metadata, and generates validated SQL + documentation. Strip everything else (Git integration, approval workflows, CI/CD) to focus on the differentiating intelligence.

## Target: Internal tool for HCM platform owners. Metadata-only access (no client row data). Multi-LLM abstraction layer.

## Domain Context
- **Industry**: Human Capital Management (HCM) — like Workday, ADP, BambooHR
- **Users**: Tool owners/operators who build reports and metrics for clients
- **Data access**: Metadata only — can see table/column structure but CANNOT query actual employee/benefits data
- **Mock schema domain**: Benefits (enrollments, plans, dependents, claims)
- **Privacy constraint**: Reinforces the PRD's metadata-only rule — here it's not just a design choice, it's a business necessity since client data is off-limits

## Mock Snowflake Schema (Benefits Domain)
Used instead of a real warehouse connection for prototyping.

### Schema: `HCM_ANALYTICS`

**`clients`** — Companies/customers using the HCM platform
- client_id (VARCHAR, PK), client_name (VARCHAR), industry (VARCHAR), country_code (VARCHAR), is_active (BOOLEAN), contract_start_date (DATE)

**`regions`** — Geographic regions with regulatory context
- region_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), region_name (VARCHAR), country_code (VARCHAR), state_province (VARCHAR), regulatory_zone (VARCHAR — e.g. ACA_applicable, non_ACA)

**`salary_bands`** — Salary tiers that drive plan eligibility
- salary_band_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), band_name (VARCHAR — e.g. band_1, executive, hourly_tier_2), min_salary (DECIMAL), max_salary (DECIMAL), currency_code (VARCHAR)

**`benefit_plans`** — Master catalog of benefit plans (varies per client)
- plan_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), plan_name (VARCHAR), plan_type (VARCHAR — medical/dental/vision/life/std/ltd/fsa/hsa), carrier_name (VARCHAR), plan_year (INT), is_active (BOOLEAN), created_at (TIMESTAMP)

**`plan_eligibility_rules`** — Which employees can enroll in which plans
- rule_id (VARCHAR, PK), plan_id (VARCHAR, FK→benefit_plans), region_id (VARCHAR, FK→regions, NULLABLE), salary_band_id (VARCHAR, FK→salary_bands, NULLABLE), employment_type (VARCHAR — full_time/part_time/contractor, NULLABLE), min_tenure_days (INT, NULLABLE), is_default (BOOLEAN)
- Note: NULL in a filter column means "all values eligible" — rules are additive

**`benefit_plan_options`** — Coverage tiers and costs within a plan (differ per client/plan)
- option_id (VARCHAR, PK), plan_id (VARCHAR, FK→benefit_plans), coverage_level (VARCHAR — employee_only/employee_spouse/employee_children/family), annual_employee_cost (DECIMAL), annual_employer_cost (DECIMAL), deductible_amount (DECIMAL), oop_max (DECIMAL), currency_code (VARCHAR)

**`employees`** — Core employee dimension
- employee_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), employee_number (VARCHAR), region_id (VARCHAR, FK→regions), department_id (VARCHAR, FK→departments), salary_band_id (VARCHAR, FK→salary_bands), job_title (VARCHAR), employment_type (VARCHAR — full_time/part_time/contractor), employment_status (VARCHAR — active/terminated/leave), hire_date (DATE), termination_date (DATE), is_benefits_eligible (BOOLEAN)

**`departments`** — Organizational hierarchy (per client)
- department_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), department_name (VARCHAR), parent_department_id (VARCHAR, FK→departments), cost_center_code (VARCHAR)

**`benefit_enrollments`** — Actual enrollment records
- enrollment_id (VARCHAR, PK), employee_id (VARCHAR, FK→employees), plan_id (VARCHAR, FK→benefit_plans), option_id (VARCHAR, FK→benefit_plan_options), enrollment_status (VARCHAR — active/terminated/waived/pending), effective_date (DATE), termination_date (DATE), enrollment_source (VARCHAR — open_enrollment/new_hire/qualifying_event), created_at (TIMESTAMP)

**`dependents`** — Employee dependents
- dependent_id (VARCHAR, PK), employee_id (VARCHAR, FK→employees), relationship (VARCHAR — spouse/child/domestic_partner), date_of_birth (DATE), is_active (BOOLEAN)

**`dependent_enrollments`** — Which dependents are on which plans
- dependent_enrollment_id (VARCHAR, PK), enrollment_id (VARCHAR, FK→benefit_enrollments), dependent_id (VARCHAR, FK→dependents), effective_date (DATE), termination_date (DATE)

**`benefit_claims`** — Claims submitted against plans
- claim_id (VARCHAR, PK), enrollment_id (VARCHAR, FK→benefit_enrollments), claim_date (DATE), claim_type (VARCHAR — in_network/out_of_network/prescription/preventive), billed_amount (DECIMAL), allowed_amount (DECIMAL), paid_amount (DECIMAL), employee_responsibility (DECIMAL), claim_status (VARCHAR — submitted/processed/denied/appealed), processed_date (DATE)

**`open_enrollment_events`** — Annual enrollment windows (per client)
- event_id (VARCHAR, PK), client_id (VARCHAR, FK→clients), plan_year (INT), open_enrollment_start (DATE), open_enrollment_end (DATE), is_active (BOOLEAN)

### PII-Flagged Columns (surfaced to AI as flagged, never values shown)
- employees.employee_number
- dependents.date_of_birth
- Any name columns if added

### Key Schema Complexity (what makes this interesting for the AI interviewer)
1. **Multi-tenancy**: Almost every query must be scoped to a client_id — the AI must always probe for which company
2. **Eligibility is conditional**: Plan availability depends on region + salary band + employment type + tenure — the AI must clarify these filters
3. **Cost varies by tier**: The same plan has different costs depending on coverage_level — the AI must ask whether the expert means employee cost, employer cost, or total
4. **Enrollment source matters**: Open enrollment vs. new hire vs. qualifying life event — different business questions require different filters
5. **Regional variance**: Plans available in California may differ from Texas — the AI must probe for geographic scope

### Realistic Interview Scenarios This Enables
1. "What's our benefits enrollment rate?" → AI must ask: which client? all plans or just medical? what counts as 'enrolled' vs 'eligible'? which regions? what time period?
2. "How much are we spending per employee on benefits?" → AI must ask: employer cost or total? which client? include waived employees in denominator? by plan type?
3. "Which plans are most popular by region?" → needs: enrollments + plans + employees + regions, definition of 'popular' (count vs. %)
4. "What's the claims cost trend by department?" → needs: claims + enrollments + employees + departments, time granularity, which client
5. "How many employees are eligible but not enrolled?" → needs: eligibility rules + enrollment status, must join plan_eligibility_rules to determine who qualifies
6. "Compare family vs. employee-only coverage costs across clients" → cross-client analysis, needs plan_options joins

## Recommended Tech Stack
- **Backend**: Python 3.12 + FastAPI (async, typed, fast to prototype)
- **LLM Abstraction**: LiteLLM (supports OpenAI, Anthropic, Azure, Bedrock via unified interface)
- **Database**: PostgreSQL 16 (interviews, entity maps, bundles)
- **Schema Cache**: PostgreSQL + SQLAlchemy (store warehouse metadata)
- **Frontend**: React 18 + TypeScript + Tailwind CSS + shadcn/ui (fast, modern component library)
- **State Management**: Zustand (lightweight, no boilerplate)
- **Real-time**: Server-Sent Events (SSE) for streaming AI responses
- **Containerization**: Docker Compose for local dev

## Prototype Scope (IN)
1. AI Interviewer with dynamic probing and stateful memory
2. Schema metadata ingestion from mock warehouse connector
3. Entity resolution against cached schema
4. Confidence scoring (improved formula)
5. Visual logic flow diagram
6. SQL + documentation generation
7. Basic review UI (read-only, no edit-in-place)

## Prototype Scope (OUT — deferred to v1)
- Git/PR integration
- Engineer edit-in-place
- Approval workflow / RBAC
- Multi-dialect SQL adapters
- dbt YAML + test generation
- Schema refresh scheduling
- Bundle versioning / immutability

## Architecture

```
[React SPA] ←SSE→ [FastAPI Backend] ←→ [PostgreSQL]
                        ↓                    ↑
                   [LiteLLM] ←→ [LLM API]   |
                        ↓                    |
                [Schema Service] ←→ [Mock Warehouse Metadata]
```

## Steps

### Phase 1: Foundation (backend core)
1. Initialize Python project with FastAPI, configure Docker Compose with PostgreSQL
2. Define data models: Interview, InterviewTurn, EntityMap, TransformationBundle (SQLAlchemy ORM)
3. Implement LLM abstraction layer using LiteLLM with a `ChatService` that handles provider switching via config
4. Build Schema Service with a **connector interface** (`BaseSchemaConnector`) and a `MockSnowflakeConnector` that returns the HCM Benefits mock schema (12 tables, FKs, PII flags) from a JSON fixture. The interface ensures a real `SnowflakeConnector` slots in later without changing consuming code.

### Phase 2: AI Interviewer (core differentiator)
5. Design the interview prompt architecture:
   - System prompt with role definition, probing rules, and output format
   - Schema context injection: relevant tables/columns injected per turn based on semantic similarity
   - Structured output: each AI turn returns JSON with `response_text`, `extracted_entities[]`, `clarification_needed[]`, `confidence_factors{}`
6. Implement stateful interview session manager:
   - Maintain a structured context object (not raw transcript) per interview
   - On each turn: update entity map, re-score confidence, detect ambiguities
   - Persist full state to PostgreSQL (survives restart)
7. Implement improved Confidence Score:
   - `score = weighted_mean(entity_resolution: 0.35, temporal_completeness: 0.20, grain_clarity: 0.20, join_validity: 0.15, filter_completeness: 0.10)`
   - Each factor scored 0.0–1.0 (continuous, not binary)
   - Blocking rule: if entity_resolution = 0 OR grain_clarity = 0 → blocked
8. Build entity resolution endpoint: given a business term + schema cache, return ranked candidate columns using fuzzy matching + LLM re-ranking

### Phase 3: SQL Generation
9. Implement SQL generator: takes confirmed EntityMap + interview context → produces clean SQL
   - Use LLM with structured prompt: provide entity map, grain, filters, aggregation logic, and schema DDL
   - Post-process: run sqlfluff lint, auto-fix formatting issues
   - Generate inline documentation comments from interview context
10. Implement logic flow diagram data structure: extract source tables, joins, filters, aggregations into a DAG JSON structure from the interview state

### Phase 4: Frontend
11. Scaffold React app with Tailwind + shadcn/ui
12. Build Interview Chat UI:
    - Chat interface with streaming responses (SSE)
    - Sidebar: real-time confidence score gauge, resolved entity list, ambiguity warnings
    - Schema browser panel (collapsible): shows available tables/columns for reference
13. Build Logic Flow Diagram component:
    - Render DAG from backend JSON using React Flow
    - Clickable nodes → show relevant interview exchange
    - Confirm/reject buttons
14. Build Review/Output page:
    - Left pane: interview summary, entity map, lineage diagram
    - Right pane: generated SQL with syntax highlighting (read-only for prototype)
    - Export/copy buttons

### Phase 5: Integration & Polish
15. Wire end-to-end flow: start interview → chat → confirm diagram → generate SQL → review
16. Add error handling: warehouse connection failures, LLM timeouts, schema-not-found
17. Add basic auth (single org — simple JWT or session-based, no RBAC yet)

## Relevant Files (to create)
- `backend/app/main.py` — FastAPI app entry point
- `backend/app/models/` — SQLAlchemy models (Interview, EntityMap, Bundle)
- `backend/app/services/chat_service.py` — LLM abstraction + interview logic
- `backend/app/services/schema_service.py` — Warehouse metadata ingestion
- `backend/app/services/scoring_service.py` — Confidence score computation
- `backend/app/services/sql_generator.py` — SQL generation from entity map
- `backend/app/api/routes/` — FastAPI route handlers
- `frontend/src/components/Chat/` — Interview chat UI
- `frontend/src/components/FlowDiagram/` — Logic flow visualization
- `frontend/src/components/Review/` — Output review page
- `docker-compose.yml` — PostgreSQL + backend + frontend

## Verification
1. **Interview flow**: Start an interview, ask about a metric (e.g., "benefits enrollment rate"), verify the AI asks clarifying questions about client, plan type, eligibility definition, region, and time window
2. **Entity resolution**: Reference "enrollment cost", verify the system surfaces `annual_employee_cost` vs `annual_employer_cost` from `benefit_plan_options` and asks which one
3. **Confidence scoring**: Submit an incomplete interview (no grain specified), verify it blocks submission. Complete the interview, verify score ≥ 80
4. **SQL generation**: From a completed interview, generate SQL. Verify it passes sqlfluff lint, references correct table/column names, includes client_id filter, and uses proper CTEs
5. **End-to-end**: Expert completes interview → confirms diagram → reviews generated SQL. Total flow under 15 minutes for a simple single-table metric

## Key Decisions
- **LiteLLM** for multi-provider LLM support (answers OQ-1 with flexibility)
- **Confidence Score improved**: weighted continuous factors instead of fragile min() of binary values
- **Mock connector first** — prove value with HCM Benefits fixture before connecting to real Snowflake
- **No Git integration in prototype** — manual copy/export of generated SQL is sufficient to prove value
- **SSE over WebSockets** — simpler, sufficient for streaming chat, no bidirectional need

## PRD Changes Applied to Prototype
1. Replaced binary Temporal_Completeness and Grain_Clarity with continuous 0–1 scores
2. Added join_validity and filter_completeness to confidence formula
3. Used weighted mean instead of min() — with blocking rules for critical-zero factors only
4. Defined interview prompt architecture (system prompt + schema injection + structured output)
5. Added schema size handling strategy (semantic similarity for table selection, not full injection)
6. Scoped to mock warehouse connector with HCM Benefits schema (12 tables)
7. Deferred dbt-specific outputs — prototype generates clean SQL + docs, not full dbt bundles
