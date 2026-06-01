import time
from dataclasses import dataclass, field


@dataclass
class ResearchTrace:
    query: str
    steps: list[tuple[str, str]] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    started_at: float = field(default_factory=time.time)

    def add(self, node: str, message: str) -> None:
        self.steps.append((node, message))

    def elapsed(self) -> float:
        return round(time.time() - self.started_at, 2)
