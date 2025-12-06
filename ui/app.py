import os, time, httpx, json
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- Clear session state ---
if st.session_state.get("_do_clear"):
    # Delete widget-backed keys BEFORE creating widgets
    for key in ["query_text", "lang_pref", "topk", "use_reranker", "topic", "index_name"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.pop("_do_clear", None)
    st.session_state.pop("last_response", None)
    st.session_state.pop("last_payload", None)
    st.rerun()

def post_query(query: str, *, index_name: str, lang_pref: list[str], k: int,
               use_reranker: bool, topic_hint: str | None):
    payload = {
        "query": (query or "").strip(),
        "k": int(k),
        "lang_pref": lang_pref or ["es","en"],
        "use_reranker": bool(use_reranker),
        "topic_hint": topic_hint or None,
        "index_name": index_name or None,
    }
    t0 = time.time()
    timeout = httpx.Timeout(15.0, connect=5.0, read=15.0, write=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.post(f"{API_URL}/query/", json=payload)
    return r, int((time.time() - t0) * 1000), payload

# --- Sidebar ---
ui_lang = st.sidebar.selectbox("UI language / Idioma de la UI", ["es","en"], index=0, key="ui_lang")
index_name = st.sidebar.text_input(
    "Index name", value=os.getenv("DEFAULT_INDEX_NAME","c300o45"), key="index_name"
)
topic = st.sidebar.selectbox("Topic / Tema", ["", "food", "culture", "gov", "health", "education"], index=1, key="topic")
lang_pref = st.sidebar.multiselect("Language preference", options=["es","en"], default=["es"], key="lang_pref")
k = st.sidebar.slider("Top-K", 1, 8, 5, key="topk")
use_reranker = st.sidebar.checkbox("Use reranker", value=False, key="use_reranker")
st.sidebar.caption("Reranker improves precision; adds ~20–40ms when enabled.")

# --- Main ---
st.title("Latino RAG Chatbot 🤖")
st.caption("Bilingual retrieval-augmented generation with citations.")

query = st.text_area("Pregunta" if ui_lang=="es" else "Question", max_chars=512, key="query_text")

col_search, col_clear = st.columns([1,1])

with col_search:
    if st.button("Buscar" if ui_lang=="es" else "Search", type="primary"):
        r, dt_ms, payload = post_query(
            query,
            index_name=index_name,
            lang_pref=lang_pref,
            k=k,
            use_reranker=use_reranker,
            topic_hint=(topic or None),
        )
        st.session_state["last_response"] = (r.status_code, dt_ms, r.text)
        st.session_state["last_payload"] = payload

with col_clear:
    if st.button("Limpiar" if ui_lang=="es" else "Clear"):
        # Mark for clearing and rerun; pre-widget block will handle deletion
        st.session_state["_do_clear"] = True
        st.rerun()

# --- Display response ---
st.subheader("Answer / Respuesta")
if "last_response" in st.session_state:
    status, dt_ms, body = st.session_state["last_response"]
    try:
        data = json.loads(body)
    except Exception:
        data = None

    if status == 200 and isinstance(data, dict):
        answer = (data.get("answer") or "").strip()
        if answer:
            st.write(answer)
        else:
            st.info("No answer returned.")

        # Citations
        st.subheader("Citations / Citas")
        cites = data.get("citations") or []
        if cites:
            for i, c in enumerate(cites, 1):
                uri = c.get("uri") or c.get("source_uri") or ""
                snip = (c.get("snippet") or "").strip()
                dt = c.get("date")
                score = c.get("score")
                st.markdown(f"**[{i}]** {snip}\n\n`{uri}` · {dt} · score={score}")
        else:
            st.info("No citations returned.")

        # Footer / debug
        route = data.get("route")
        index = data.get("index") or (st.session_state.get("index_name") or "n/a")
        rerank = data.get("reranker")
        st.caption(f"route={route} · index={index} · reranker={rerank} · k={st.session_state.get('topk')} · {dt_ms} ms")
        st.subheader("Reproduce (cURL)")
        st.code(
            f"curl -s -X POST {API_URL}/query/ -H 'Content-Type: application/json' "
            f"-d '{json.dumps(st.session_state.get('last_payload') or {}, ensure_ascii=False)}'",
            language="bash",
        )
    else:
        # Non-200 or non-JSON: show raw body
        st.error(f"HTTP {status}")
        st.code(body, language="json")
