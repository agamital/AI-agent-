"""
Investment Research Agent — Streamlit UI
Integrated with Intent Router for Hebrew/English natural language support.
"""

import os
import sys
from datetime import datetime
import streamlit as st

# Ensure src is in path
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from investment_agent.agents.research_agent import InvestmentResearchAgent
from investment_agent.agents.intent_router import parse_intent
from investment_agent.validation.ticker_validator import validate_ticker

# ── Page Setup ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investment Research Agent",
    page_icon="📈",
    layout="wide",
)

# Custom CSS for the mockup design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root {
  --acc:#5849f0; --accSoft:#ecebfe;
  --pos:#0e9f6e; --posSoft:#e7f6ef;
  --neg:#e0342a; --negSoft:#fdeceb;
  --bd:#e9e9ee; --mut:#6c6c76; --fnt:#a2a2ac;
}
html, body, [class*=\"css\"] { font-family:'IBM Plex Sans', sans-serif; }
.ir-header { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:15px 22px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; }
.ir-logo { width:34px; height:34px; border-radius:9px; background:var(--acc); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:600; }
.ir-report { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
</style>
""", unsafe_allow_html=True)

# ── Session State ───────────────────────────────────────────────────────────

if "agent" not in st.session_state:
    st.session_state.agent = InvestmentResearchAgent()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class=\"ir-header\">
  <div style=\"display:flex; align-items:center; gap:12px;\">
    <div class=\"ir-logo\">IR</div>
    <div>
      <div style=\"font-weight:600;\">Investment Research Agent</div>
      <div style=\"font-size:12px; color:var(--mut);\">Powered by Llama 3.3 & Intent Router</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Main Chat Interface ─────────────────────────────────────────────────────

# Display history
for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(text)

# Input
user_input = st.chat_input("Ask about a stock (e.g., 'Analyze Apple' or 'תנתח את אנבידיה')...")

if user_input:
    # 1. Show user message
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Process with Intent Router
    with st.spinner("Parsing request..."):
        intent_data = parse_intent(st.session_state.agent.client, user_input)

    # 3. Handle Intent
    with st.chat_message("assistant"):
        if intent_data.get("intent") == "analyze" and intent_data.get("ticker"):
            ticker = intent_data["ticker"]
            peers = intent_data.get("peers", [])

            st.write(f"🔍 Detected Intent: **Analyze {ticker}**" + (f" vs {', '.join(peers)}" if peers else ""))

            with st.spinner(f"Generating research report for {ticker}..."):
                report = st.session_state.agent.analyse(ticker, peers=peers)
                st.markdown(f'<div class=\"ir-report\">{report}</div>', unsafe_allow_html=True)
                st.session_state.chat_history.append(("assistant", report))

        elif intent_data.get("intent") == "followup":
            with st.spinner("Thinking..."):
                answer = st.session_state.agent.follow_up(user_input)
                st.markdown(answer)
                st.session_state.chat_history.append(("assistant", answer))

        else:
            msg = "I didn't quite catch that. Try asking to 'Analyze [Stock]' or ask a follow-up question."
            if intent_data.get("original_language") == "he":
                msg = "לא הצלחתי להבין את הבקשה. נסה לבקש 'נתח את [מניה]' או שאל שאלת המשך."
            st.write(msg)
            st.session_state.chat_history.append(("assistant", msg))
"""
