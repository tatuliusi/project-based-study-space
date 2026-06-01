import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.graph import research

st.set_page_config(page_title="Research Agent", page_icon="🔍", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f1117; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
.source-card { background: #1e1e2e; border-radius: 6px; padding: 10px 14px; margin: 6px 0; border-left: 3px solid #7c3aed; }
.source-card a { color: #a78bfa; text-decoration: none; font-weight: 600; }
.source-card .snippet { color: #9ca3af; font-size: 0.85em; margin-top: 4px; }
.finding-card { background: #111827; border-radius: 6px; padding: 12px 16px; margin: 8px 0; }
.finding-text { color: #e5e7eb; font-size: 0.95em; }
.step-badge { display: inline-block; background: #1f2937; color: #9ca3af; border-radius: 4px; padding: 2px 8px; font-size: 0.78em; margin-bottom: 3px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("Research Agent")
    st.caption("LangGraph + Tavily + GPT-4o-mini")
    st.divider()
    st.markdown("""
**Graph**
```
START → plan → search → evaluate
  ↑ (if gaps)       ↓ (if sufficient)
  └──────────── generate → END
```
""")
    st.divider()
    st.markdown("**Trace**")
    trace_placeholder = st.empty()

st.title("Multi-source Research Agent")
st.caption("Searches the web iteratively until coverage is sufficient, then writes a structured report.")

query = st.text_input("Research question", placeholder="e.g. What are the latest advances in open-source LLMs?")

if st.button("Research", type="primary") and query.strip():
    with st.spinner("Researching — this may take 30–60 seconds..."):
        report, trace = research(query.strip())

    steps_md = ""
    for node, msg in trace.steps:
        steps_md += f'<span class="step-badge">{node}</span> {msg}<br>'
    steps_md += f"<br>⏱ {trace.elapsed()}s &nbsp;|&nbsp; {trace.total_tokens:,} tokens &nbsp;|&nbsp; ${trace.total_cost_usd:.4f}"
    trace_placeholder.markdown(steps_md, unsafe_allow_html=True)

    st.subheader(report.title)
    st.write(report.summary)

    st.subheader("Key Findings")
    for finding in report.key_findings:
        st.markdown(
            f'<div class="finding-card"><div class="finding-text">{finding.point}</div></div>',
            unsafe_allow_html=True,
        )
        for src in finding.sources:
            st.markdown(
                f'<div class="source-card"><a href="{src.url}" target="_blank">{src.title}</a>'
                f'<div class="snippet">{src.snippet}</div></div>',
                unsafe_allow_html=True,
            )

    with st.expander("All sources"):
        for src in report.sources:
            st.markdown(f"- [{src.title}]({src.url})")

    st.subheader("Conclusion")
    st.write(report.conclusion)
