import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "rag_agent.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)

log = logging.getLogger("rag_agent")


@dataclass
class TraceEvent:
    step: str
    detail: str


@dataclass
class QueryTrace:
    query: str
    events: list[TraceEvent] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def add(self, step: str, detail: str) -> None:
        self.events.append(TraceEvent(step=step, detail=detail))
        log.info("[%s] %s", step, detail)
