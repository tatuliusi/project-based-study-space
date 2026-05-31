import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.graph import ask
from src.retriever import build_vectorstore, load_vectorstore

st.set_page_config(page_title="DocMind", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    /* Global */
    .block-container { padding: 2rem 3rem 1rem 3rem; max-width: 900px; }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Page title */
    .app-title { font-size: 1.6rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0; }
    .app-sub   { font-size: 0.85rem; color: #888; margin-top: 2px; margin-bottom: 1.5rem; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #0f0f0f; }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    section[data-testid="stSidebar"] .stButton>button {
        background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
        color: #e0e0e0 !important; width: 100%; transition: background 0.15s;
    }
    section[data-testid="stSidebar"] .stButton>button:hover { background: #252525; }

    /* Sidebar section label */
    .sidebar-label {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: #555 !important; margin-bottom: 0.4rem;
    }

    /* Document status pill */
    .status-pill {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 500; margin-top: 6px;
    }
    .status-ready   { background: #0d2b1d; color: #4ade80; border: 1px solid #166534; }
    .status-pending { background: #1c1500; color: #facc15; border: 1px solid #713f12; }

    /* Cost line */
    .cost-line {
        font-size: 0.72rem; color: #555; text-align: center;
        padding: 6px 0 2px 0; letter-spacing: 0.02em;
    }
    .cost-line span { color: #888; }

    /* Chat messages */
    .stChatMessage { border-radius: 12px; margin-bottom: 0.5rem; }

    /* Trace expander */
    .streamlit-expanderHeader {
        font-size: 0.78rem !important; color: #666 !important;
        background: transparent !important; padding: 4px 0 !important;
    }
    .streamlit-expanderContent { padding: 0.5rem 0 !important; }

    /* Trace step badges */
    .trace-row { display: flex; align-items: flex-start; gap: 10px; padding: 4px 0; font-size: 0.82rem; }
    .trace-badge {
        display: inline-block; padding: 1px 8px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 600; white-space: nowrap; margin-top: 1px;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    .badge-retrieve { background: #1e3a5f; color: #60a5fa; }
    .badge-grade    { background: #3b2000; color: #fb923c; }
    .badge-generate { background: #0d2b1d; color: #4ade80; }
    .badge-rewrite  { background: #2d1b5e; color: #c084fc; }
    .trace-detail   { color: #ccc; line-height: 1.5; }

    /* Empty state */
    .empty-state {
        text-align: center; padding: 4rem 2rem; color: #444;
        border: 1px dashed #222; border-radius: 16px; margin-top: 2rem;
    }
    .empty-state h3 { color: #666; font-size: 1.1rem; margin-bottom: 0.5rem; }
    .empty-state p  { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# Session state
for key, default in [
    ("store", None), ("messages", []),
    ("session_cost", 0.0), ("session_tokens", 0), ("doc_count", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.store is None:
    st.session_state.store = load_vectorstore()


def render_trace(trace) -> None:
    badge_class = {"retrieve": "badge-retrieve", "grade": "badge-grade",
                   "generate": "badge-generate", "rewrite": "badge-rewrite"}
    html = ""
    for event in trace.events:
        cls = badge_class.get(event.step, "badge-retrieve")
        html += (
            f'<div class="trace-row">'
            f'<span class="trace-badge {cls}">{event.step}</span>'
            f'<span class="trace-detail">{event.detail}</span>'
            f'</div>'
        )
    st.markdown(html, unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-label">Knowledge base</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload files", type=["pdf", "txt"],
        accept_multiple_files=True, label_visibility="collapsed",
    )

    if uploaded and st.button("Index documents"):
        with st.spinner("Indexing..."):
            tmp_paths = []
            for f in uploaded:
                suffix = ".pdf" if f.name.endswith(".pdf") else ".txt"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(f.read())
                    tmp_paths.append(tmp.name)
            st.session_state.store = build_vectorstore(tmp_paths)
            st.session_state.doc_count = len(uploaded)
            for p in tmp_paths:
                os.unlink(p)

    if st.session_state.store:
        n = st.session_state.doc_count
        label = f"{n} file{'s' if n != 1 else ''} indexed" if n else "Vector store loaded"
        st.markdown(f'<div class="status-pill status-ready">● {label}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill status-pending">○ No documents yet</div>', unsafe_allow_html=True)

    st.markdown("<br>" * 8, unsafe_allow_html=True)

    tokens = st.session_state.session_tokens
    cost = st.session_state.session_cost
    st.markdown(
        f'<div class="cost-line"><span>{tokens:,} tokens · ${cost:.5f}</span></div>',
        unsafe_allow_html=True,
    )

# Main
st.markdown('<div class="app-title">🧠 DocMind</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">Ask questions about your documents. Answers are cited and grounded.</div>', unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("""
    <div class="empty-state">
        <h3>No conversation yet</h3>
        <p>Upload documents in the sidebar, then ask anything about them.</p>
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "trace" in msg:
            trace = msg["trace"]
            with st.expander(f"↳ {len(trace.events)} steps · {trace.total_tokens} tokens · ${trace.total_cost_usd:.5f}"):
                render_trace(trace)

if query := st.chat_input("Ask about your documents..."):
    if not st.session_state.store:
        st.error("Upload and index documents first using the sidebar.")
    else:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.chat_message("assistant"):
            with st.spinner(""):
                answer, trace = ask(query, st.session_state.store)
            st.write(answer)
            with st.expander(f"↳ {len(trace.events)} steps · {trace.total_tokens} tokens · ${trace.total_cost_usd:.5f}"):
                render_trace(trace)

        st.session_state.session_cost += trace.total_cost_usd
        st.session_state.session_tokens += trace.total_tokens
        st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
        st.rerun()
