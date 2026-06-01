from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI

from src.schemas import CoverageVerdict, ResearchReport

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_coverage_checker = _llm.with_structured_output(CoverageVerdict)
_report_writer = _llm.with_structured_output(ResearchReport)
_tavily = TavilySearchResults(max_results=5)

PLAN_PROMPT = """You are a research strategist. Generate 3–5 targeted web search queries to research the following topic.

Topic: {query}
Iteration: {iteration}
{gaps_section}
Return only the queries, one per line. No numbering, no extra text."""

EVALUATE_PROMPT = """You are evaluating whether collected research results adequately cover a topic.

Topic: {query}
Iteration: {iteration}

Collected results so far:
{results_text}

Assess:
- sufficient: true if coverage is broad and deep enough to write a quality report
- gaps: list specific missing angles (empty if sufficient)
- confidence: 0.0–1.0 score for how well the topic is covered"""

REPORT_PROMPT = """You are a research analyst. Write a comprehensive research report from the following sources.

Topic: {query}

Sources:
{results_text}

Produce:
- title: concise report title
- summary: 2–3 sentence overview
- key_findings: list of distinct points, each with supporting sources
- sources: all sources used
- conclusion: 2–3 sentence takeaway"""


def plan_node(state: dict) -> dict:
    trace = state["trace"]
    query = state["query"]
    iteration = state.get("iteration", 1)
    verdict = state.get("coverage_verdict")

    gaps_section = ""
    if verdict and verdict.gaps:
        gaps_list = "\n".join(f"- {g}" for g in verdict.gaps)
        gaps_section = f"Gaps identified in previous iteration:\n{gaps_list}\nFocus new queries on filling these gaps."

    trace.add("plan", f"iteration {iteration}: planning queries")
    raw = _llm.invoke(PLAN_PROMPT.format(query=query, iteration=iteration, gaps_section=gaps_section)).content.strip()
    queries = [line.strip() for line in raw.splitlines() if line.strip()]
    trace.add("plan", f"planned {len(queries)} queries")
    return {"planned_queries": queries}


def search_node(state: dict) -> dict:
    trace = state["trace"]
    queries = state["planned_queries"]
    accumulated = list(state.get("search_results", []))

    for q in queries:
        trace.add("search", f"'{q}'")
        results = _tavily.invoke(q)
        if isinstance(results, list):
            for r in results:
                r["_query"] = q
            accumulated.extend(results)
            trace.add("search", f"→ {len(results)} result(s)")

    return {"search_results": accumulated}


def evaluate_node(state: dict) -> dict:
    trace = state["trace"]
    query = state["query"]
    results = state["search_results"]
    iteration = state.get("iteration", 1)

    results_text = _format_results(results)
    trace.add("evaluate", f"checking coverage over {len(results)} result(s)")
    verdict: CoverageVerdict = _coverage_checker.invoke(
        EVALUATE_PROMPT.format(query=query, iteration=iteration, results_text=results_text)
    )
    status = "sufficient" if verdict.sufficient else f"insufficient (confidence={verdict.confidence:.2f})"
    trace.add("evaluate", f"{status}, gaps: {len(verdict.gaps)}")
    return {"coverage_verdict": verdict, "iteration": iteration + 1}


def generate_node(state: dict) -> dict:
    trace = state["trace"]
    query = state["query"]
    results = state["search_results"]

    trace.add("generate", f"writing report from {len(results)} sources")
    results_text = _format_results(results)
    report: ResearchReport = _report_writer.invoke(
        REPORT_PROMPT.format(query=query, results_text=results_text)
    )
    trace.add("generate", "report ready")
    return {"report": report}


def route_after_evaluate(state: dict) -> str:
    verdict = state.get("coverage_verdict")
    iteration = state.get("iteration", 1)
    if not verdict or verdict.sufficient or iteration > 3:
        return "generate"
    return "plan"


def _format_results(results: list[dict]) -> str:
    lines = []
    for r in results:
        lines.append(f"[{r.get('title', 'No title')}] {r.get('url', '')}")
        lines.append(f"  {r.get('content', '')[:400]}")
    return "\n".join(lines)
