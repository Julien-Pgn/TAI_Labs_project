"""Streamlit page for the /ask API.

Run it with:  streamlit run streamlit_app.py
Set the API address in the sidebar, or with the API_URL environment variable.
"""
import json
import os

import requests
import streamlit as st

MODELS = ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1-mini"]  # same allowlist as the API

st.set_page_config(page_title="TAI Labs · Ask", page_icon="🌼")

with st.sidebar:
    st.header("Settings")
    api_url = (
        st.text_input(
            "API URL",
            os.getenv("API_URL", "http://localhost:8000"),
            type="password",  # hidden, so screenshots don't leak your live URL
            help="Your Render URL, e.g. https://your-service.onrender.com",
        )
        .strip()
        .rstrip("/")
    )
    model = st.selectbox("Model", MODELS, help="gpt-4.1-nano is the cheapest")
    force_bad = st.toggle("Force a bad first answer", help="Shows the guardrail catching bad output, then retrying")
    st.caption("On Render's free plan the API sleeps when idle, so the first request can take about a minute.")

st.title("🌼 Ask anything")
st.caption("A typed `/ask` endpoint: structured answer, guardrail, tokens and cost.")

with st.form("ask"):
    question = st.text_area(
        "Your question",
        placeholder="What is Retrieval-Augmented Generation in one sentence?",
        max_chars=2000,
    )
    submitted = st.form_submit_button("Ask", type="primary")

if submitted and question.strip():
    payload = {"question": question.strip(), "model": model, "force_bad": force_bad}
    with st.spinner("Thinking…"):
        try:
            r = requests.post(f"{api_url}/ask", json=payload, timeout=120)
            st.session_state.result = (payload, r.status_code, r.json())
        except (requests.RequestException, ValueError) as e:  # unreachable, or not a JSON reply
            st.session_state.result = (payload, None, str(e))

# Kept in session_state so the result stays on screen when the page reruns.
if "result" in st.session_state:
    payload, status, data = st.session_state.result

    if status is None:
        st.error(f"Can't reach the API. Check the API URL in the sidebar.\n\n{data}")
    elif status != 200:
        detail = data.get("detail", data) if isinstance(data, dict) else data
        st.error(f"The API returned an error ({status}): {detail}")
    else:
        answer = data["answer"]
        with st.container(border=True):
            st.markdown(answer["answer"])

        cols = st.columns(4)
        cols[0].metric("Tokens", data["tokens_used"])
        cols[1].metric("Cost", f"${data['cost_usd']:.6f}")
        cols[2].metric("Latency", f"{data['latency_ms'] / 1000:.1f} s")
        cols[3].metric("Confidence", f"{answer['confidence']:.0%}")
        st.caption(f"Model: `{data['model']}` · Needs sources: {'yes' if answer['sources_needed'] else 'no'}")

        st.subheader("Guardrail")
        for a in data["attempts"]:
            if a["valid"]:
                st.success(f"Attempt {a['attempt']}: output passed validation", icon="✅")
            else:
                st.error(f"Attempt {a['attempt']}: bad output caught. {a['error']}", icon="🛡️")

    with st.expander("Raw JSON response"):
        if isinstance(data, (dict, list)):
            st.json(data)
        else:
            st.write(data)

    with st.expander("Same request with curl"):
        body = json.dumps(payload).replace("'", "'\\''")  # escape quotes for the shell
        st.code(
            f"curl -s -X POST {api_url}/ask \\\n  -H 'Content-Type: application/json' \\\n  -d '{body}'",
            language="bash",
        )
