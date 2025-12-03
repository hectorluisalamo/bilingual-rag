import os, time, json, textwrap, httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

def post_query(q: str, k: int = 5, langs= ["es"], use_reranker=True, topic_hint=None, index_name=None):
    payload = {
        "query": q,
        "k": k,
        "lang_pref": langs or ["es", "en"],
        "use_reranker": use_reranker,
        "topic_hint": topic_hint,
        "index_name": index_name,
    }
    t0 = time.time()
    timeout = httpx.Timeout(connect=5.0, read=10.0)
    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.post(f"{API_URL}/query/", json=payload)
            r.raise_for_status()
            dt = int((time.time() - t0) * 1000)
            return r.json(), dt, payload
        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            if attempt == 0:
                continue
            raise

st.set_page_config(page_title="Latino RAG", page_icon="🫓", layout="centered")

# --- Sidebar controls ---
st.sidebar.title("Latino RAG - Demo")
ui_lang = st.sidebar.selectbox("UI language / Idioma de la UI", ["es", "en"], index=0)
index_name = st.sidebar.text_input("Index name", os.getenv("DEFAULT_INDEX_NAME", "c300o45"))
topic_hint = st.sidebar.selectbox(
    "Topic / Tema", ["", "food", "culture", "health", "civics", "education"], index=1
)
langs = st.sidebar.multiselect("Language preference", ["es", "en"], default=["es"])
k = st.sidebar.slider("Top-K", min_value=1, max_value=8, value=5, step=1)
use_reranker = st.sidebar.checkbox("Use reranker", value=True)
st.sidebar.caption("Reranker improves precision; adds ~20-40ms.")

st.title("Latino RAG Chatbot")
st.caption("Bilingual retrieval-augmented generation with citations.")

q_label = "Pregunta" if ui_lang=="es" else "Question"
query = st.text_area(q_label, "¿Qué es una arepa?", height=90, max_chars=512)

col1, col2 = st.columns([1,1])
with col1:
    go = st.button("Buscar" if ui_lang=="es" else "Search", type="primary")
with col2:
    clear = st.button("Limpiar" if ui_lang=="es" else "Clear")
if clear:
    st.session_state.pop("last", None)
    st.experimental_rerun()

if go:
    if not query.strip():
        st.warning("Escribe una pregunta." if ui_lang=="es" else "Type a question.")
    else:
        r, dt_ms, payload = post_query(query)
        try:
            data = r.json()
        except Exception:
            st.error(f"Bad response ({r.status_code}).")
            st.code(r.text)
            st.stop()

        if r.status_code != 200:
            st.error(f"Error {r.status_code}: {data}")
            st.stop()

        st.session_state["last"] = dict(data=data, dt_ms=dt_ms, payload=payload)

# --- Results ---
if "last" in st.session_state:
    data = st.session_state["last"]["data"]
    dt_ms = st.session_state["last"]["dt_ms"]
    payload = st.session_state["last"]["payload"]

    st.subheader("Answer / Respuesta")
    st.write(data.get("answer",""))
    st.caption(f"route={data.get('route')} · index={payload['index_name']} · k={payload['k']} · reranker={payload['use_reranker']} · {int(dt_ms)} ms · request_id={data.get('request_id')}")

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
