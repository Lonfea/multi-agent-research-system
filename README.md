# Multi-Agent Research System

A research workflow with specialized researcher, writer, fact-checker, and supervisor roles, explicit consensus rules, a persisted audit trail, and a human approval gate.

## Workflow

Topic -> Researcher -> Writer -> Fact Checker -> Supervisor -> Consensus Gate -> Human Approval

CrewAI runs the agent team. SQLite stores every important event so a completed report can be traced back to the task outputs, fact-check verdict, supervisor decision, and human review.

## Reliability design

The system does not treat "multiple agents" as automatic correctness.

A report reaches the human approval state only when all three conditions hold:

1. the fact-check verification score exceeds the configured threshold;
2. the supervisor approves the report;
3. the fact checker reports no unsupported claims.

Otherwise the run is marked needs_revision.

## Human approval

POST /runs/{run_id}/decision persists the reviewer decision and feedback. The audit endpoint returns the complete event history.

## Run

    cd ai-engineering-lab/multi-agent-research
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env
    uvicorn app.main:app --reload

Required credentials:
- OPENAI_API_KEY
- SERPER_API_KEY

## API

- POST /research — start a research run
- GET /runs/{run_id} — report plus complete audit trail
- POST /runs/{run_id}/decision — approve or reject with reviewer feedback

## Production upgrades

- async execution and job queue;
- source-level citation schema rather than Markdown-only links;
- retry policy by failure type;
- eval dataset for factuality and source quality;
- OpenTelemetry traces across agent and tool calls.
