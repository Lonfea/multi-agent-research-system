import os

from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.audit import AuditStore
from app.models import HumanDecision, ResearchRequest
from app.pipeline import ResearchPipeline


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    research_model: str = "openai/gpt-5.6-terra"
    supervisor_model: str = "openai/gpt-5.6-sol"
    audit_db: str = "research_audit.db"
    fact_check_threshold: float = 0.80


settings = Settings()
store = AuditStore(settings.audit_db)
pipeline = ResearchPipeline(
    research_model=settings.research_model,
    supervisor_model=settings.supervisor_model,
    fact_check_threshold=settings.fact_check_threshold,
)

app = FastAPI(title="Multi-Agent Research System", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest) -> dict:
    if not os.getenv("SERPER_API_KEY"):
        raise HTTPException(status_code=503, detail="SERPER_API_KEY is required for web research.")

    run_id = store.create_run(request.topic)
    try:
        outcome = pipeline.run(request.topic)
        for index, output in enumerate(outcome.task_outputs):
            store.event(run_id, "agent_task_output", {"task_index": index, "output": output})

        store.event(run_id, "fact_check", outcome.fact_check.model_dump())
        store.event(run_id, "supervisor_decision", outcome.supervisor.model_dump())

        status = "pending_human_approval" if outcome.consensus_approved else "needs_revision"
        store.set_result(run_id, status, outcome.report)
        return {
            "run_id": run_id,
            "status": status,
            "consensus_approved": outcome.consensus_approved,
            "verification_score": outcome.fact_check.verification_score,
            "supervisor": outcome.supervisor.model_dump(),
            "report": outcome.report,
        }
    except Exception as exc:
        store.event(run_id, "run_failed", {"error": type(exc).__name__, "message": str(exc)})
        store.set_result(run_id, "failed", "")
        raise HTTPException(status_code=500, detail="Research run failed.") from exc


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    run["events"] = store.get_events(run_id)
    return run


@app.post("/runs/{run_id}/decision")
def human_decision(run_id: str, decision: HumanDecision) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] not in {"pending_human_approval", "needs_revision"}:
        raise HTTPException(status_code=409, detail="Run is not awaiting a human decision.")

    store.human_decision(run_id, decision.approved, decision.feedback)
    return {
        "run_id": run_id,
        "status": "approved" if decision.approved else "rejected",
        "feedback": decision.feedback,
    }
