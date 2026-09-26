import json
import sqlite3
import uuid
from datetime import UTC, datetime


class AuditStore:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                status TEXT NOT NULL,
                final_report TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def create_run(self, topic: str) -> str:
        run_id = str(uuid.uuid4())
        now = self._now()
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs(id, topic, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, topic, "running", now, now),
            )
        self.event(run_id, "run_created", {"topic": topic})
        return run_id

    def event(self, run_id: str, event_type: str, payload: dict) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO events(run_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(payload, default=str), self._now()),
            )

    def set_result(self, run_id: str, status: str, report: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE runs SET status=?, final_report=?, updated_at=? WHERE id=?",
                (status, report, self._now(), run_id),
            )
        self.event(run_id, "status_changed", {"status": status})

    def human_decision(self, run_id: str, approved: bool, feedback: str) -> None:
        status = "approved" if approved else "rejected"
        with self.conn:
            self.conn.execute(
                "UPDATE runs SET status=?, updated_at=? WHERE id=?",
                (status, self._now(), run_id),
            )
        self.event(
            run_id,
            "human_decision",
            {"approved": approved, "feedback": feedback},
        )

    def get_run(self, run_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_events(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT event_type, payload, created_at FROM events WHERE run_id=? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
