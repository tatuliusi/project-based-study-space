import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

from src.graph.state import (
    BranchState,
    FactCheckResult,
    Finding,
    PipelineState,
    Report,
    ReportSection,
    Source,
)

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_tavily: TavilyClient | None = None


def _get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient()
    return _tavily


# ---------------------------------------------------------------------------
# decompose_topic
# ---------------------------------------------------------------------------

def decompose_topic(state: PipelineState) -> dict[str, Any]:
    prompt = f"""Break the following research topic into 4-6 focused, non-overlapping sub-topics.
Return a JSON array of strings and nothing else.

Topic: {state["topic"]}"""

    response = _llm.invoke([HumanMessage(content=prompt)])
    try:
        sub_topics: list[str] = json.loads(response.content)
    except json.JSONDecodeError:
        sub_topics = [state["topic"]]
        logger.warning("Failed to parse sub-topics JSON; using full topic as single branch")

    return {"sub_topics": sub_topics, "findings": [], "status": "running"}


# ---------------------------------------------------------------------------
# research_branch  (runs N times in parallel via Send)
# ---------------------------------------------------------------------------

def research_branch(state: BranchState) -> dict[str, Any]:
    sub_topic = state["sub_topic"]
    tavily = _get_tavily()

    try:
        results = tavily.search(query=sub_topic, max_results=5)
        raw_results = results.get("results", [])
    except Exception as exc:
        logger.error("Tavily search failed for '%s': %s", sub_topic, exc)
        return {
            "findings": [
                Finding(
                    sub_topic=sub_topic,
                    summary="Research failed due to search error.",
                    confidence=0.0,
                )
            ]
        }

    sources = [
        Source(
            url=r.get("url", ""),
            title=r.get("title", ""),
            snippet=r.get("content", "")[:400],
        )
        for r in raw_results
    ]

    snippet_block = "\n\n".join(
        f"[{i+1}] {s.title}\n{s.snippet}" for i, s in enumerate(sources)
    )
    summary_prompt = f"""Summarize the key findings for this sub-topic based on the sources below.
Be factual and concise (3-5 sentences). Sub-topic: {sub_topic}

Sources:
{snippet_block}"""

    summary_response = _llm.invoke([HumanMessage(content=summary_prompt)])
    summary = summary_response.content.strip()

    confidence = min(1.0, len(sources) / 5)

    return {
        "findings": [
            Finding(
                sub_topic=sub_topic,
                summary=summary,
                sources=sources,
                confidence=confidence,
            )
        ]
    }


# ---------------------------------------------------------------------------
# fact_check
# ---------------------------------------------------------------------------

def fact_check(state: PipelineState) -> dict[str, Any]:
    findings = state["findings"]
    if not findings:
        return {"fact_check_results": [], "status": "running"}

    claims_block = "\n".join(
        f"- [{f.sub_topic}] {f.summary}" for f in findings if f.confidence > 0
    )
    prompt = f"""You are a fact-checking agent. For each claim below, assess whether it is likely
accurate based on common knowledge and source credibility. Return a JSON array where each item has:
  "claim": string,
  "verified": boolean,
  "confidence": float (0.0-1.0),
  "supporting_sources": list of relevant URLs (can be empty)

Claims:
{claims_block}"""

    response = _llm.invoke(
        [
            SystemMessage(content="Return only valid JSON, no markdown fences."),
            HumanMessage(content=prompt),
        ]
    )

    try:
        raw: list[dict] = json.loads(response.content)
        results = [FactCheckResult(**item) for item in raw]
    except Exception as exc:
        logger.warning("Fact-check JSON parse failed: %s", exc)
        results = [
            FactCheckResult(claim=f.summary, verified=True, confidence=f.confidence)
            for f in findings
        ]

    # Apply credibility scores back to sources in findings
    credibility_map: dict[str, float] = {}
    for r in results:
        for url in r.supporting_sources:
            credibility_map[url] = r.confidence

    for finding in findings:
        for source in finding.sources:
            if source.url in credibility_map:
                source.domain_credibility = credibility_map[source.url]

    return {"fact_check_results": results, "status": "running"}


# ---------------------------------------------------------------------------
# synthesize
# ---------------------------------------------------------------------------

def synthesize(state: PipelineState) -> dict[str, Any]:
    verified_findings = [
        f for f in state["findings"] if f.confidence >= 0.4
    ]

    if not verified_findings:
        verified_findings = state["findings"]

    combined = "\n\n".join(
        f"### {f.sub_topic}\n{f.summary}" for f in verified_findings
    )
    prompt = f"""Synthesize the following research findings on the topic "{state['topic']}" into
a coherent narrative. Resolve contradictions by noting them. Output 3-5 well-formed paragraphs.

Findings:
{combined}"""

    response = _llm.invoke([HumanMessage(content=prompt)])
    return {"_synthesis": response.content.strip()}


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

def format_report(state: PipelineState) -> dict[str, Any]:
    synthesis: str = state.get("_synthesis", "")  # type: ignore[arg-type]
    topic = state["topic"]

    all_sources: list[Source] = []
    seen_urls: set[str] = set()
    for f in state["findings"]:
        for s in f.sources:
            if s.url not in seen_urls:
                all_sources.append(s)
                seen_urls.add(s.url)

    sections_prompt = f"""Given this synthesized research on "{topic}", create a structured report.
Return JSON with this shape:
{{
  "executive_summary": "string",
  "sections": [
    {{"title": "string", "content": "string", "citations": ["url1", "url2"]}}
  ]
}}

Synthesis:
{synthesis}

Available source URLs: {json.dumps([s.url for s in all_sources[:10]])}"""

    response = _llm.invoke(
        [
            SystemMessage(content="Return only valid JSON, no markdown fences."),
            HumanMessage(content=sections_prompt),
        ]
    )

    try:
        data = json.loads(response.content)
        sections = [ReportSection(**s) for s in data.get("sections", [])]
        executive_summary = data.get("executive_summary", synthesis[:500])
    except Exception as exc:
        logger.warning("format_report JSON parse failed: %s", exc)
        sections = [ReportSection(title="Summary", content=synthesis)]
        executive_summary = synthesis[:500]

    verified = [r for r in state["fact_check_results"] if r.verified]
    confidence_score = (
        sum(r.confidence for r in verified) / len(verified) if verified else 0.5
    )

    report = Report(
        job_id=state["job_id"],
        topic=topic,
        executive_summary=executive_summary,
        sections=sections,
        bibliography=all_sources,
        confidence_score=round(confidence_score, 2),
    )

    return {"report": report, "status": "running"}


# ---------------------------------------------------------------------------
# render_pdf  (returns PDF bytes stored under state key for store_artifact)
# ---------------------------------------------------------------------------

def render_pdf(state: PipelineState) -> dict[str, Any]:
    from jinja2 import Environment, PackageLoader, select_autoescape
    from weasyprint import HTML

    report = state["report"]
    if report is None:
        return {"artifact_url": None}

    try:
        env = Environment(
            loader=PackageLoader("src", "templates"),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("report.html")
    except Exception:
        # Fallback: inline minimal template
        from jinja2 import Environment as _Env
        env = _Env()
        template = env.from_string(_FALLBACK_TEMPLATE)

    html_str = template.render(report=report)
    pdf_bytes: bytes = HTML(string=html_str).write_pdf()

    return {"_pdf_bytes": pdf_bytes}


_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body{font-family:sans-serif;margin:2cm;} h1{color:#1a1a2e;}</style>
</head><body>
<h1>{{ report.topic }}</h1>
<p><strong>Executive Summary:</strong> {{ report.executive_summary }}</p>
{% for section in report.sections %}
<h2>{{ section.title }}</h2>
<p>{{ section.content }}</p>
{% endfor %}
<h2>Bibliography</h2>
<ul>{% for s in report.bibliography %}<li><a href="{{ s.url }}">{{ s.title }}</a></li>{% endfor %}</ul>
</body></html>"""


# ---------------------------------------------------------------------------
# store_artifact
# ---------------------------------------------------------------------------

def store_artifact(state: PipelineState) -> dict[str, Any]:
    import os
    import redis as redis_lib

    report = state["report"]
    pdf_bytes: bytes | None = state.get("_pdf_bytes")  # type: ignore[assignment]
    job_id = state["job_id"]

    try:
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        ttl = int(os.getenv("REPORT_TTL_SECONDS", "86400"))

        if report:
            r.setex(f"report:{job_id}:json", ttl, report.model_dump_json())

        if pdf_bytes:
            r.setex(f"report:{job_id}:pdf", ttl, pdf_bytes)

        artifact_url = f"/reports/{job_id}/pdf"
        r.setex(f"report:{job_id}:status", ttl, "done")
    except Exception as exc:
        logger.error("store_artifact failed: %s", exc)
        artifact_url = None

    return {"artifact_url": artifact_url, "status": "done"}
