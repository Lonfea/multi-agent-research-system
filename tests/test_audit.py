from app.audit import AuditStore


def test_audit_trail_records_human_decision(tmp_path):
    store = AuditStore(str(tmp_path / "audit.db"))
    run_id = store.create_run("Test topic")
    store.set_result(run_id, "pending_human_approval", "Draft")
    store.human_decision(run_id, True, "Looks good")

    run = store.get_run(run_id)
    events = store.get_events(run_id)

    assert run["status"] == "approved"
    assert any(e["event_type"] == "human_decision" for e in events)
