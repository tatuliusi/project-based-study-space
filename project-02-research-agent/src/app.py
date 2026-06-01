import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.graph import research

st.set_page_config(page_title="Research Agent", page_icon="🔬", layout="wide")

st.markdown("""
<style>
/* ---------- global ---------- */
html, body, [data-testid="stApp"] { background: #f8fafc; }
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] strong { color: #e2e8f0 !important; }

/* ---------- hero ---------- */
.hero { text-align: center; padding: 2.5rem 0 1.5rem; }
.hero h1 { font-size: 2.2rem; font-weight: 800; color: #0f172a; margin: 0; }
.hero p { color: #64748b; margin-top: 0.4rem; font-size: 1rem; }

/* ---------- metrics row ---------- */
.metrics-row { display: flex; gap: 12px; margin: 1.2rem 0; flex-wrap: wrap; }
.metric-chip {
    background: white; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 10px 18px; flex: 1; min-width: 100px; text-align: center;
}
.metric-chip .val { font-size: 1.35rem; font-weight: 700; color: #0ea5e9; }
.metric-chip .lbl { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }

/* ---------- finding card ---------- */
.finding {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 16px 20px; margin: 10px 0;
    border-left: 4px solid #0ea5e9;
}
.finding-num { font-size: 0.72rem; font-weight: 700; color: #0ea5e9; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.finding-text { color: #1e293b; font-size: 0.95rem; line-height: 1.6; }

/* ---------- source card ---------- */
.source {
    background: #f1f5f9; border-radius: 7px; padding: 9px 14px; margin: 5px 0 5px 16px;
    border-left: 3px solid #bae6fd;
}
.source a { color: #0284c7; font-weight: 600; font-size: 0.87rem; text-decoration: none; }
.source a:hover { text-decoration: underline; }
.source .snip { color: #64748b; font-size: 0.8rem; margin-top: 3px; line-height: 1.4; }

/* ---------- summary box ---------- */
.summary-box {
    background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
    border: 1px solid #bfdbfe; border-radius: 10px; padding: 18px 22px; margin-bottom: 1rem;
}
.summary-box p { color: #1e293b; font-size: 1rem; line-height: 1.7; margin: 0; }

/* ---------- conclusion box ---------- */
.conclusion-box {
    background: #fafafa; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 18px 22px; margin-top: 0.5rem;
}
.conclusion-box p { color: #374151; font-size: 0.95rem; line-height: 1.7; margin: 0; }

/* ---------- source list ---------- */
.source-list-item { padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.88rem; }
.source-list-item a { color: #0284c7; }
</style>
""", unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 Research Agent")
    st.caption("v1.0 · LangGraph + Tavily")
    st.divider()
    st.markdown("""
**How it works**

```
plan → search → evaluate
  ↑ gaps          ↓ sufficient
  └──────── generate
```

The agent loops up to **3 iterations**, filling identified gaps before writing the report.
""")
    st.divider()
    st.markdown("**Live trace**")
    trace_box = st.empty()

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔬 Research Agent</h1>
  <p>Ask any question. The agent searches the web, evaluates coverage, and writes a cited report.</p>
</div>
""", unsafe_allow_html=True)

col_input, col_btn = st.columns([5, 1])
with col_input:
    query = st.text_input(
        "Question",
        placeholder="e.g. What are the latest advances in open-source LLMs?",
        label_visibility="collapsed",
    )
with col_btn:
    run = st.button("Research →", type="primary", use_container_width=True)

# ── run ───────────────────────────────────────────────────────────────────────
if run and query.strip():
    trace_lines: list[str] = []

    NODE_ICONS = {"plan": "🗂", "search": "🌐", "evaluate": "🔎", "generate": "✍️"}

    with st.status("Researching...", expanded=True) as status:
        def on_step(node: str, msg: str) -> None:
            icon = NODE_ICONS.get(node, "•")
            st.write(f"{icon} **{node}** — {msg}")
            trace_lines.append(f"{icon} **{node}** — {msg}")

        report, trace = research(query.strip(), on_step=on_step)
        status.update(label="Done!", state="complete", expanded=False)

    # update sidebar trace
    trace_box.markdown("\n\n".join(trace_lines) + f"\n\n---\n⏱ {trace.elapsed()}s · {trace.total_tokens:,} tokens · ${trace.total_cost_usd:.4f}")

    # ── metrics row ───────────────────────────────────────────────────────────
    iterations = sum(1 for n, _ in trace.steps if n == "evaluate")
    source_count = len(report.sources)

    st.markdown(f"""
<div class="metrics-row">
  <div class="metric-chip"><div class="val">{iterations}</div><div class="lbl">Iterations</div></div>
  <div class="metric-chip"><div class="val">{source_count}</div><div class="lbl">Sources</div></div>
  <div class="metric-chip"><div class="val">{trace.elapsed()}s</div><div class="lbl">Time</div></div>
  <div class="metric-chip"><div class="val">${trace.total_cost_usd:.4f}</div><div class="lbl">Cost</div></div>
</div>
""", unsafe_allow_html=True)

    # ── tabs ──────────────────────────────────────────────────────────────────
    tab_overview, tab_findings, tab_sources = st.tabs(["Overview", "Findings", "All Sources"])

    with tab_overview:
        st.markdown(f"### {report.title}")
        st.markdown(f'<div class="summary-box"><p>{report.summary}</p></div>', unsafe_allow_html=True)
        st.markdown("**Conclusion**")
        st.markdown(f'<div class="conclusion-box"><p>{report.conclusion}</p></div>', unsafe_allow_html=True)

    with tab_findings:
        for i, finding in enumerate(report.key_findings, 1):
            sources_html = "".join(
                f'<div class="source"><a href="{s.url}" target="_blank">{s.title}</a>'
                f'<div class="snip">{s.snippet}</div></div>'
                for s in finding.sources
            )
            st.markdown(f"""
<div class="finding">
  <div class="finding-num">Finding {i}</div>
  <div class="finding-text">{finding.point}</div>
</div>
{sources_html}
""", unsafe_allow_html=True)

    with tab_sources:
        st.caption(f"{source_count} sources collected")
        for i, src in enumerate(report.sources, 1):
            st.markdown(
                f'<div class="source-list-item">{i}. <a href="{src.url}" target="_blank">{src.title}</a></div>',
                unsafe_allow_html=True,
            )
