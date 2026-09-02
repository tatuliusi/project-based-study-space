from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class StepEvent:
    node: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    output_keys: list[str] = field(default_factory=list)
    iteration: int = 0


@dataclass
class ProgressTracker:
    task_id: str
    events: list[StepEvent] = field(default_factory=list)

    def record(self, node: str, output: dict[str, Any], iteration: int = 0) -> None:
        self.events.append(
            StepEvent(
                node=node,
                output_keys=list(output.keys()),
                iteration=iteration,
            )
        )

    def current_step(self) -> str:
        if not self.events:
            return "pending"
        return self.events[-1].node

    def elapsed_seconds(self) -> float:
        if len(self.events) < 2:
            return 0.0
        delta = self.events[-1].timestamp - self.events[0].timestamp
        return delta.total_seconds()

    def iteration_count(self) -> int:
        test_events = [e for e in self.events if e.node in ("run_tests", "patch")]
        return len([e for e in test_events if e.node == "run_tests"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "current_step": self.current_step(),
            "elapsed_seconds": self.elapsed_seconds(),
            "iteration_count": self.iteration_count(),
            "steps": [
                {
                    "node": e.node,
                    "timestamp": e.timestamp.isoformat(),
                    "output_keys": e.output_keys,
                    "iteration": e.iteration,
                }
                for e in self.events
            ],
        }
