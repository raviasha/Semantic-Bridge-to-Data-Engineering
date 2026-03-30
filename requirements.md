PRODUCT REQUIREMENTS DOCUMENT
Semantic Bridge Application
Eliminating Translation Lag Between Domain Experts and Data Engineers
Version 1.0  •  Status: Ready for Development  •  March 29, 2026

DOCUMENT OWNER	TBD – Assign before sprint kick-off	ENGINEERING LEAD	TBD
TARGET RELEASE	TBD – Scope sprint 0 first	PRIORITY	P0 – Core Platform

1. Problem Statement
Domain experts hold business knowledge that data engineers need to build correct transformations. Today this knowledge travels via ad-hoc Slack threads, ambiguous Jira tickets, and verbal walkthroughs — creating rework cycles, misaligned metrics, and untracked lineage. The Semantic Bridge Application closes this loop by structuring the expert interview, grounding it against real schema metadata, and auto-generating validated engineering artifacts.

Definition: Translation Lag
The elapsed time and error rate between a domain expert articulating a business metric and a data engineer correctly implementing it in the warehouse. This PRD targets a measured reduction of ≥70%.

2. Goals & Non-Goals
▌ 2.1  Goals
•	Capture unambiguous business intent from domain experts via a structured AI interview.
•	Ground every metric definition against live warehouse schema metadata before it reaches an engineer.
•	Produce ready-to-merge dbt transformation bundles (SQL + YAML + tests) from validated interview transcripts.
•	Give engineers a side-by-side intent ↔ code review portal with in-app edit capability.
•	Automate PR creation in GitHub/GitLab with complete lineage provenance.

▌ 2.2  Non-Goals (v1.0)
•	Does not execute SQL against production data — metadata only.
•	Does not replace the data engineer; it augments their context.
•	Does not ingest or display PII from warehouse tables.
•	Does not handle streaming / real-time pipeline orchestration.
•	Does not support manual schema uploads in v1 — schema source must be a connected warehouse.

3. User Personas
PERSONA	ROLE	PRIMARY GOAL	PAIN TODAY
Expert	Product Manager, Finance Analyst, Business Stakeholder	Express a metric clearly without knowing SQL	Tickets misunderstood; constant back-and-forth with eng
Engineer	Data / Analytics Engineer	Receive unambiguous, schema-validated requirements	Vague specs, missing field names, undocumented assumptions
Reviewer	Data Lead / Architect	Audit lineage and approve transformations confidently	No audit trail linking business rationale to model code

4. Functional Requirements
▌ FR-1  Context-Aware AI Interviewer
The AI agent must act as an active interrogator, not a passive prompt receiver.
FR-1.1  Dynamic Probing
•	The agent must detect under-specified terms and issue follow-up questions before proceeding.
◦	Example trigger: Expert says 'Monthly Active Users' → Agent must ask: (a) which event name defines 'active', (b) lookback window: 28-day rolling vs. calendar month, (c) deduplication key.
◦	Probing depth: Minimum 1 clarifying question per unresolved entity; maximum 3 rounds before surfacing a structured ambiguity list to the expert.
FR-1.2  Ambiguity Scoring
•	Every in-progress interview must carry a real-time Confidence Score (0–100).
◦	Score < 60: Interview is flagged as incomplete; submission to engineering queue is blocked.
◦	Score 60–79: Submission is allowed but flagged as 'Needs Review' in the engineering portal.
◦	Score ≥ 80: Submission proceeds as 'Ready for Implementation'.
◦	Score formula: Computed as: min(Entity_Resolution_Rate, Temporal_Completeness, Grain_Clarity) × 100. Any factor at 0 blocks submission.
•	Score rationale must be surfaced to the expert (e.g. 'Grain not confirmed — which level of aggregation do you need?').
FR-1.3  Stateful Interview Memory
•	The session must maintain a running context model across all turns of the interview.
•	A late-stage correction (e.g., changing the deduplication key in turn 8) must retroactively update all earlier assumptions and re-score affected entities.
•	State must be persisted server-side; browser refresh must restore in-progress interview.

▌ FR-2  Metadata Grounding (Schema RAG)
All AI reasoning must be anchored to real warehouse schema — never to assumed structure.
FR-2.1  Schema Ingestion
•	System must connect to the target warehouse and fetch: table DDL, column names + types, column descriptions (if present), primary keys, and foreign key relationships.
•	Schema cache must refresh on a configurable schedule (default: hourly) or on-demand via UI.
•	Only structural metadata may be stored — no row-level data, no sample values.
FR-2.2  Entity Resolution
•	When an expert references a business term (e.g. 'Customer ID'), the agent must resolve it to ≥ 1 candidate column(s) from the schema.
•	If multiple candidates exist (e.g., customer_id, crm_uuid, global_account_fk), the agent must present them and require the expert to select one before proceeding.
•	Unresolvable terms must decrement the Confidence Score and trigger a blocking clarification.
FR-2.3  PII Safety
•	The system must never ingest, store, or process actual table data — only DDL and column-level metadata.
•	Columns tagged with PII classifications in the warehouse metadata must be surfaced to the agent as 'PII-flagged' without exposing their values.

▌ FR-3  Visual Transformation Preview
FR-3.1  Logic Flow Diagram
•	On reaching Confidence Score ≥ 60, the UI must render a Logic Flow Diagram showing: Source table(s) → Filter conditions → Join logic → Aggregation → Output grain.
•	Diagram nodes must be clickable; clicking a node opens the relevant interview exchange for context.
•	The expert must be presented with a binary confirm/reject action on the diagram before submission.
•	A rejected diagram routes back to the interview with a pre-filled correction prompt.

▌ FR-4  Standardized Output — Transformation Bundle
Upon expert confirmation, the system generates a versioned, immutable Transformation Bundle.
ARTIFACT	CONTENT	ACCEPTANCE CRITERIA
SQL / dbt Model	Clean, modular SQL following company style guide (CTEs, snake_case, no SELECT *)	Passes sqlfluff lint with zero errors on target dialect
YAML Documentation	Auto-generated column descriptions sourced from interview transcript; model-level description included	Every column has a non-empty description; model has an interview_id reference
Data Quality Tests	Suggested dbt tests: not_null, unique, accepted_values, relationships — inferred from interview logic	≥ 1 test per primary key column; accepted_values generated where the expert enumerated values
Lineage Tag	meta.interview_id, meta.generated_at, meta.confidence_score attached to every model	Tag present and queryable in warehouse information_schema after deployment

▌ FR-5  Engineering Review Portal
FR-5.1  Dual-Pane View
•	Left pane: Summarized business intent, resolved entity map, and lineage diagram extracted from the interview.
•	Right pane: Generated SQL with syntax highlighting.
•	Panes must be independently scrollable and resizable.
FR-5.2  Edit-in-Place
•	Engineers must be able to edit SQL directly in the right pane before approval.
•	All edits must be tracked (diff view available) and saved as a new bundle revision.
•	A revision comment is required before saving an engineer edit.
FR-5.3  Approval Workflow
•	Only users with the 'Data Engineer' or 'Data Lead' role may approve a bundle.
•	Approval triggers PR generation (FR-6). Rejection routes back to the expert with a mandatory comment.

▌ FR-6  Git-Integrated CI/CD Workflow
FR-6.1  PR Generation
•	On engineer approval, the system must open a Pull Request in the configured repository automatically.
•	PR must include: SQL file, YAML documentation file, test file, and a PR description auto-populated from the interview summary.
•	PR branch naming convention: semantic-bridge/{interview_id}/{model_name}.
FR-6.2  Supported Platforms
•	GitHub (v1.0) and GitLab (v1.0) via configurable OAuth integration.
•	Additional providers (Bitbucket, Azure DevOps) via the adapter pattern (see TR-4).

5. Technical Requirements
ID	CATEGORY	SPECIFICATION
TR-1	LLM — Stateful Reasoning	The LLM context window must persist the full interview transcript. Late-stage corrections must trigger a re-evaluation pass over all prior extracted entities. Implementation must use a structured context object (not raw transcript string) to enable targeted updates.
TR-2	Security — Metadata-Only Access	The AI layer must receive only: table names, column names, data types, descriptions, and key constraints. Row-level data must never be fetched, cached, or passed to any LLM API. A data access audit log must record every schema fetch with timestamp and requesting user.
TR-3	Provenance — Lineage Tagging	Every generated dbt model must carry: meta.interview_id (UUID), meta.semantic_bridge_version (semver), meta.confidence_score (int), meta.generated_at (ISO 8601 UTC). These tags must survive through warehouse deployment and be queryable.
TR-4	Extensibility — SQL Dialect Adapters	SQL generation must be decoupled from dialect-specific syntax via an Adapter interface. v1.0 must ship adapters for: Snowflake, BigQuery, Databricks SQL. Each adapter must implement: generate_cte(), generate_date_filter(), generate_aggregation(), format_identifier(). New adapters must be addable without modifying core generation logic.
TR-5	Performance	Schema RAG retrieval: p95 < 2s. Confidence Score update: p95 < 500ms after each turn. Bundle generation (SQL + YAML + tests): p95 < 10s. PR creation: p95 < 5s.

6. Validation Guardrail — Submission Blocker Logic
To prevent hallucinated or structurally invalid transformations from reaching the engineering queue, the system enforces the following gate. If any factor equals zero, the bundle is blocked.

Neat Transformation Score  =  Entity_Resolution_Rate  ×  Temporal_Completeness  ×  Grain_Clarity
If any factor = 0  →  bundle submission BLOCKED

FACTOR	DEFINITION	ZERO CONDITION
Entity_Resolution_Rate	% of business entities in the request that are mapped to a confirmed warehouse column	Any entity is unresolved or the expert declined to select a candidate
Temporal_Completeness	1 if a date range or lookback window is explicitly defined; 0 otherwise	No time dimension defined for any time-series metric
Grain_Clarity	1 if the output grain (row-level definition) is confirmed by the expert; 0 otherwise	Expert has not confirmed what one row in the output represents

7. Core Data Model
ENTITY	KEY FIELDS	NOTES
Interview	interview_id (UUID)	Owns the full conversation state, Confidence Score history, and resolved entity map. Immutable once submitted.
EntityMap	interview_id, term, column_fqn	Maps each business term to its fully qualified column name (schema.table.column). One row per resolved entity.
TransformationBundle	bundle_id, interview_id, version	Versioned artifact container. Stores SQL, YAML, and test files. Immutable after engineer approval.
BundleRevision	revision_id, bundle_id, editor	Records engineer edits pre-approval. Stores diff, timestamp, and mandatory comment.
PullRequest	pr_id, bundle_id, platform	Tracks the external PR (GitHub/GitLab). Stores URL, status, and merge SHA once merged.

8. Open Questions & Decisions Required
#	QUESTION	OWNER	TARGET DATE
OQ-1	Which LLM provider is approved for processing interview transcripts? (OpenAI, Anthropic, Azure OpenAI, self-hosted?)	Security + Engineering Lead	Before Sprint 1
OQ-2	What is the company SQL style guide that the dbt models must conform to? (Provide reference or link.)	Data Engineering Lead	Before Sprint 1
OQ-3	Should the schema cache be push-based (warehouse triggers a webhook on DDL change) or pull-based (scheduled refresh)?	Data Platform Team	Sprint 0 retro
OQ-4	What is the RBAC model? Are 'Expert' and 'Engineer' roles synced from an existing IdP (Okta, etc.) or managed within the app?	Security / Platform	Sprint 0 retro
OQ-5	What is the target Confidence Score threshold to mark a bundle as 'Ready' vs. 'Needs Review'? (Default proposed: 80 / 60.)	Product Owner	Sprint 1 kick-off

9. Explicitly Out of Scope (v1.0)
•	Manual schema upload / file-based DDL import.
•	Streaming or near-real-time pipeline generation.
•	Automated test execution or CI feedback loop integration (PR checks only in v1).
•	Multi-language SQL (Python models, Spark, etc.) — dbt SQL only.
•	Direct warehouse write-back or model deployment — the system produces artifacts for human-approved deployment.

10. Document Revision History
VERSION	DATE	AUTHOR	SUMMARY
1.0	Mar 29, 2026	Generated via Semantic Bridge PRD Refinement	Initial release — refined from stakeholder requirements brief

