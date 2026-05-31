import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.graph import ask
from src.retriever import build_vectorstore, load_vectorstore

st.set_page_config(page_title="RAG Q&A Agent", page_icon="📄")
st.title("RAG Q&A Agent")
st.caption("Upload documents, ask questions, get cited answers.")

if "store" not in st.session_state:
    st.session_state.store = load_vectorstore()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_cost" not in st.session_state:
    st.session_state.session_cost = 0.0
if "session_tokens" not in st.session_state:
    st.session_state.session_tokens = 0

with st.sidebar:
    st.header("Documents")
    uploaded = st.file_uploader("Upload PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True)

    if uploaded and st.button("Index documents"):
        with st.spinner("Indexing..."):
            tmp_paths = []
            for f in uploaded:
                suffix = ".pdf" if f.name.endswith(".pdf") else ".txt"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(f.read())
                    tmp_paths.append(tmp.name)

            st.session_state.store = build_vectorstore(tmp_paths)
            for p in tmp_paths:
                os.unlink(p)

        st.success(f"Indexed {len(uploaded)} file(s).")

    if st.session_state.store:
        st.success("Vector store ready.")
    else:
        st.warning("No documents indexed yet.")

    st.divider()
    st.header("Session costs")
    st.metric("Total tokens", f"{st.session_state.session_tokens:,}")
    st.metric("Total cost", f"${st.session_state.session_cost:.5f}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "trace" in msg:
            trace = msg["trace"]
            with st.expander(f"Trace — {trace.total_tokens} tokens / ${trace.total_cost_usd:.5f}"):
                for event in trace.events:
                    st.markdown(f"**{event.step}** — {event.detail}")

if query := st.chat_input("Ask a question about your documents..."):
    if not st.session_state.store:
        st.error("Upload and index documents first.")
    else:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, trace = ask(query, st.session_state.store)
            st.write(answer)
            with st.expander(f"Trace — {trace.total_tokens} tokens / ${trace.total_cost_usd:.5f}"):
                for event in trace.events:
                    st.markdown(f"**{event.step}** — {event.detail}")

        st.session_state.session_cost += trace.total_cost_usd
        st.session_state.session_tokens += trace.total_tokens
        st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
        st.rerun()
