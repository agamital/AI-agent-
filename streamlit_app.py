import os
import sys
from datetime import datetime
import streamlit as st

# Ensure src is in path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from investment_agent.agents.research_agent import InvestmentResearchAgent
from investment_agent.agents.intent_router import parse_intent
from investment_agent.validation.ticker_validator import validate_ticker

# -- Page Setup --
st.set_page_config(page_title='Investment Research Agent', page_icon='📈', layout='wide')

# Custom CSS - Using double braces for CSS and variable interpolation for dimensions
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root {{ --acc:#5849f0; --bd:#e9e9ee; --mut:#6c6c76; }}
html, body, [class*='css'] {{ font-family:'IBM Plex Sans', sans-serif; }}
.ir-header {{ background:#fff; border:1px solid var(--bd); border-radius:14px; padding:15px 22px; margin-bottom:18px; display:flex; align-items:center; gap:12px; }}
.ir-logo {{ width:34px; height:34px; border-radius:9px; background:var(--acc); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:600; }}
.ir-report {{ background:#fff; border:1px solid var(--bd); border-radius:14px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
</style>""", unsafe_allow_html=True)

if 'agent' not in st.session_state:
    st.session_state.agent = InvestmentResearchAgent()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

st.markdown('<div class="ir-header"><div class="ir-logo">IR</div><div><div style="font-weight:600;">Investment Research Agent</div><div style="font-size:12px; color:var(--mut);">Powered by Llama 3.3</div></div></div>', unsafe_allow_html=True)

for role, text in st.session_state.chat_history:
    with st.chat_message(role): st.markdown(text)

user_input = st.chat_input('Ask about a stock...')
if user_input:
    st.session_state.chat_history.append(('user', user_input))
    with st.chat_message('user'): st.markdown(user_input)
    with st.spinner('Thinking...'):
        intent_data = parse_intent(st.session_state.agent.client, user_input)
    with st.chat_message('assistant'):
        if intent_data.get('intent') == 'analyze' and intent_data.get('ticker'):
            ticker = intent_data['ticker']
            with st.spinner(f'Analyzing {ticker}...'):
                report = st.session_state.agent.analyse(ticker, peers=intent_data.get('peers', []))
                st.markdown(f'<div class="ir-report">{report}</div>', unsafe_allow_html=True)
                st.session_state.chat_history.append(('assistant', report))
        elif intent_data.get('intent') == 'followup':
            answer = st.session_state.agent.follow_up(user_input)
            st.markdown(answer)
            st.session_state.chat_history.append(('assistant', answer))
        else:
            msg = "I didn't catch that. Try 'Analyze Apple'."
            st.write(msg)
            st.session_state.chat_history.append(('assistant', msg))
