from __future__ import annotations

from typing import Any, Callable

from ..contracts import ActionRequest
from ..memory import LocalStore


class ToolExecutor:
    def __init__(self, store: LocalStore):
        self.store = store
        self._tools: dict[str, Callable[[dict[str, Any]], str]] = {
            "create_reminder": self.create_reminder,
            "schedule_medication_reminder": self.schedule_medication_reminder,
            "list_reminders": self.list_reminders,
            "complete_reminder": self.complete_reminder,
            "mood_check_in": self.mood_check_in,
            "log_hydration": self.log_hydration,
            "add_appointment_note": self.add_appointment_note,
            "create_appointment": self.create_appointment,
            "add_wellness_note": self.add_wellness_note,
            "wellness_summary": self.wellness_summary,
        }

    def execute(self, action: ActionRequest) -> str:
        if action.tool not in self._tools:
            raise ValueError(f"tool is not allowed: {action.tool}")
        return self._tools[action.tool](action.arguments)

    def create_reminder(self, args: dict[str, Any]) -> str:
        title, when = args.get("title"), args.get("when")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(when, str)
            or not when.strip()
        ):
            raise ValueError("title and when are required")
        with self.store.connect() as db:
            cursor = db.execute(
                "INSERT INTO reminders(title,due_at) VALUES (?,?)", (title[:200], when[:100])
            )
        return f"Reminder {cursor.lastrowid} created"

    def list_reminders(self, args: dict[str, Any]) -> str:
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT id,title,due_at FROM reminders WHERE completed=0 ORDER BY id"
            ).fetchall()
        return (
            "; ".join(f"{r['id']}: {r['title']} ({r['due_at']})" for r in rows)
            or "No active reminders"
        )

    def schedule_medication_reminder(self, args: dict[str, Any]) -> str:
        medication, when = args.get("medication"), args.get("when")
        if not isinstance(medication, str) or not medication.strip():
            raise ValueError("medication name is required")
        return self.create_reminder({"title": f"Take {medication}", "when": when})

    def complete_reminder(self, args: dict[str, Any]) -> str:
        try:
            reminder_id = int(args["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("numeric reminder id required") from exc
        with self.store.connect() as db:
            changed = db.execute(
                "UPDATE reminders SET completed=1 WHERE id=?", (reminder_id,)
            ).rowcount
        if not changed:
            raise ValueError("reminder not found")
        return "Reminder completed"

    def _wellness(self, kind: str, value: Any) -> str:
        if not isinstance(value, (str, int, float)) or str(value).strip() == "":
            raise ValueError("value required")
        with self.store.connect() as db:
            db.execute("INSERT INTO wellness(kind,value) VALUES (?,?)", (kind, str(value)[:200]))
        return f"{kind.replace('_', ' ').title()} logged"

    def mood_check_in(self, args: dict[str, Any]) -> str:
        return self._wellness("mood", args.get("mood"))

    def log_hydration(self, args: dict[str, Any]) -> str:
        return self._wellness("hydration_ml", args.get("milliliters"))

    def add_appointment_note(self, args: dict[str, Any]) -> str:
        note = args.get("note")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("note required")
        with self.store.connect() as db:
            db.execute("INSERT INTO appointment_notes(note) VALUES (?)", (note[:2000],))
        return "Appointment note saved"

    def create_appointment(self, args: dict[str, Any]) -> str:
        title, when, note = args.get("title"), args.get("when"), args.get("note", "")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(when, str)
            or not when.strip()
        ):
            raise ValueError("appointment title and when are required")
        if not isinstance(note, str):
            raise ValueError("appointment note must be text")
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO appointments(title,scheduled_at,note) VALUES (?,?,?)",
                (title[:200], when[:100], note[:2000]),
            )
        return "Appointment saved"

    def add_wellness_note(self, args: dict[str, Any]) -> str:
        note = args.get("note")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("wellness note is required")
        with self.store.connect() as db:
            db.execute("INSERT INTO wellness_notes(note) VALUES (?)", (note[:2000],))
        return "Wellness note saved"

    def wellness_summary(self, args: dict[str, Any]) -> str:
        with self.store.connect() as db:
            counts = dict(db.execute("SELECT kind,COUNT(*) FROM wellness GROUP BY kind").fetchall())
        return (
            ", ".join(f"{key}: {value}" for key, value in counts.items()) or "No wellness entries"
        )
