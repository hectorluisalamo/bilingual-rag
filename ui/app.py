import os, time, json, textwrap, httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

def post_query(query: str, *, k: int = 5, lang_pref: list[str], use_reranker: bool,
               topic_hint: str, index_name: str | None):
    payload = {
        "query": query,
        "k": int(k),
        "lang_pref": lang_pref or ["es", "en"],
        "use_reranker": bool(use_reranker),
        "topic_hint": topic_hint,
        "index_name": index_name,
    }
    t0 = time.time()
    timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=10.0)

    for attempt in range(2):  # tiny retry
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.post(f"{API_URL}/query/", json=payload)
            r.raise_for_status()
            dt_ms = int((time.time() - t0) * 1000)
            return r, dt_ms, payload
        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            if attempt == 0:
                continue
            raise
        except httpx.HTTPStatusError as e:
            # still return response for UI to show payload
            return e.response, int((time.time() - t0) * 1000), payload

st.set_page_config(page_title="Latino RAG", page_icon="🫓", layout="centered")

# --- Sidebar controls ---
st.sidebar.title("Latino RAG - Demo")
ui_lang = st.sidebar.selectbox("UI language / Idioma de la UI", ["es", "en"], index=0, key="ui_lang")
index_name = st.sidebar.text_input("Index name", os.getenv("DEFAULT_INDEX_NAME", "c300o45"), key="index_name")
topic = st.sidebar.selectbox(
    "Topic / Tema", ["", "food", "culture", "health", "civics", "education"], index=1, key="topic"
)
lang_pref = st.sidebar.multiselect("Language preference", ["es", "en"], default=["es"], key="lang_pref")
k = st.sidebar.slider("Top-K", min_value=1, max_value=8, value=5, step=1, key="topk")
use_reranker = st.sidebar.checkbox("Use reranker", value=False, key="use_reranker")
st.sidebar.caption("Reranker improves precision; adds ~20-40ms.")

st.title("Latino RAG Chatbot")
st.caption("Bilingual retrieval-augmented generation with citations.")

q_label = "Pregunta" if ui_lang=="es" else "Question"
query = st.text_area(q_label, "¿Qué es una arepa?", height=90, max_chars=512, key="query")

col_search, col_clear = st.columns([1,1])
with col_search:
    go = st.button("Buscar" if ui_lang=="es" else "Search", type="primary")
if go:
    if not query.strip():
        st.warning("Escribe una pregunta." if ui_lang=="es" else "Type a question.")
    else:
        r, dt_ms, payload = post_query(
            query,
            k=k,
            lang_pref=lang_pref,
            use_reranker=use_reranker,
            topic_hint=(topic or None),
            index_name=index_name,
        )
        try:
            data = r.json()
        except Exception:
            st.error(f"Bad response ({r.status_code}).")
            st.code(r.text)
            st.stop()

        if r.status_code != 200:
            st.error(f"Error {r.status_code}: {data}")
            st.stop()

        st.session_state["last_response"] = (r.status_code, dt_ms, r.text)
        st.session_state["last_payload"] = payload
        
with col_clear:
    clear = st.button("Limpiar" if ui_lang=="es" else "Clear")
if clear:
        # Full reset of relevant session keys
        for key in ["query_text","last_response","last_payload"]:
            st.session_state.pop(key, None)
        # Reset sidebar toggles
        st.session_state.update({
            "lang_pref": ["es"],
            "topk": 5,
            "use_reranker": False,
            "topic": "",
        })
        st.experimental_rerun()
        
# --- Results ---
if "last_response" in st.session_state:
    status, dt_ms, body = st.session_state["last_response"]

    st.subheader("Answer / Respuesta")
    st.write(data.get("answer", "No answer returned."))
    st.caption(body if status != 200 else "")

    st.subheader("Citations / Citas")
    cits = data.get("citations", [])
    if not cits:
        st.info("No citations returned.")
    else:
        for i, c in enumerate(cits, 1):
            with st.expander(f"[{i}] {c['uri']}"):
                st.write(c.get("snippet",""))
                meta = []
                if c.get("date"): meta.append(f"date={c['date']}")
                if c.get("score") is not None: meta.append(f"score={round(c['score'],3)}")
                if meta: st.caption(" · ".join(meta))
                st.code(c["uri"])

    st.subheader("Reproduce (cURL)")
    curl = f"""curl -s -X POST {API_URL}/query/ -H "Content-Type: application/json" -d '{json.dumps(payload, ensure_ascii=False)}' | jq"""
    st.code(textwrap.dedent(curl))
