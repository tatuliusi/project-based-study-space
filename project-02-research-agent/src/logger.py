import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ResearchTrace:
    query: str
    steps: list[tuple[str, str]] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    started_at: float = field(default_factory=time.time)
    on_step: Callable[[str, str], None] | None = None

    def add(self, node: str, message: str) -> None:
        self.steps.append((node, message))
        if self.on_step:
            self.on_step(node, message)

    def elapsed(self) -> float:
        return round(time.time() - self.started_at, 2)
