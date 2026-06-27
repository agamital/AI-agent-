"""
Investment Research Agent — Streamlit UI (visual + chat)
Charts/tables come from raw data (no LLM tokens).
LLM only writes the Bull/Bear/Bottom-line narrative + follow-ups.
"""

import os
import sys
from datetime import datetime

import streamlit as st

src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from investment_agent.agents.research_agent import InvestmentResearchAgent
from investment_agent.agents.intent_router import parse_intent
from investment_agent.agents.structured_output import analyse_structured
from investment_agent.reporting.charts import (
    price_chart, rsi_gauge, metrics_bar, snapshot_metrics, usage_bar,
)
from investment_agent.llm.client import USAGE

# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Investment Research Agent", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root { --acc:#5849f0; --accSoft:#ecebfe; --pos:#0e9f6e; --posSoft:#e7f6ef;
        --neg:#e0342a; --negSoft:#fdeceb; --bd:#e9e9ee; --mut:#6c6c76; --fnt:#a2a2ac; --chip:#f1f1f4; }
html, body, [class*="css"] { font-family:'IBM Plex Sans', sans-serif; }
.mono { font-family:'IBM Plex Mono', monospace; }
.stApp { background:#f4f4f7; }
.main .block-container { padding-top:1.2rem; max-width:1080px; }
.ir-header { display:flex; align-items:center; justify-content:space-between; background:#fff;
  border:1px solid var(--bd); border-radius:14px; padding:14px 22px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.ir-logo { width:34px; height:34px; border-radius:9px; background:var(--acc); display:flex; align-items:center;
  justify-content:center; color:#fff; font:600 14px 'IBM Plex Mono',monospace; box-shadow:0 2px 8px rgba(88,73,240,.35); }
.ir-title { font-size:15.5px; font-weight:600; }
.ir-sub { font-size:12px; color:var(--mut); margin-top:1px; }
.ir-pill { display:inline-flex; align-items:center; gap:6px; font-size:11px; color:var(--mut);
  padding:6px 11px; border:1px solid var(--bd); border-radius:999px; background:#fafafb; }
.ir-pill-warn { display:inline-flex; align-items:center; gap:7px; font-size:11px; color:#9a7011;
  padding:6px 12px; border:1px solid #f1e3b8; border-radius:999px; background:#fdf6e0; }
.ir-dot { width:6px; height:6px; border-radius:50%; display:inline-block; }
section[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--bd); }
.ir-side-label { font:600 10.5px 'IBM Plex Mono',monospace; letter-spacing:.1em; text-transform:uppercase; color:var(--fnt); margin:4px 0 8px; }
.ir-card { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:16px 20px; box-shadow:0 1px 3px rgba(0,0,0,.06); margin:8px 0; }
.ir-rephead { display:flex; align-items:center; gap:14px; }
.ir-repicon { width:48px; height:48px; border-radius:12px; background:var(--chip); display:flex; align-items:center;
  justify-content:center; font:600 16px 'IBM Plex Mono',monospace; }
.ir-bull { border:1px solid var(--pos); border-radius:14px; padding:14px 18px; background:var(--posSoft); }
.ir-bear { border:1px solid var(--neg); border-radius:14px; padding:14px 18px; background:var(--negSoft); }
.ir-welcome { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:32px 28px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.ir-chip-row { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:14px; }
.ir-chip { font:500 12px 'IBM Plex Mono',monospace; padding:7px 13px; border-radius:8px; background:var(--accSoft); color:var(--acc); direction:rtl; }
.ir-warn-banner { display:flex; gap:12px; padding:13px 16px; border-radius:12px; background:#fdf6e0; border:1px solid #f1e3b8; margin:8px 0; font-size:12.5px; color:#8a6a16; }
.ir-err-banner { padding:14px 18px; border-radius:12px; background:var(--negSoft); border:1px solid #f4c4c0; margin:8px 0; font-size:13px; color:#9a3a34; }
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
def _keys_present():
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))

for key, default in [("agent", None), ("chat", []), ("current_ticker", None), ("last_run", None), ("pending_input", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

def get_agent():
    if st.session_state.agent is None:
        st.session_state.agent = InvestmentResearchAgent()
    return st.session_state.agent

# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="ir-header">
  <div style="display:flex; align-items:center; gap:12px;">
    <div class="ir-logo">IR</div>
    <div><div class="ir-title">Investment Research Agent</div>
    <div class="ir-sub">Autonomous equity research across SEC filings, market data &amp; news</div></div>
  </div>
  <div style="display:flex; align-items:center; gap:9px;">
    <div class="ir-pill"><span class="mono" style="color:var(--acc); font-weight:600;">Llama 3.3 70B</span>
      <span style="color:var(--fnt);">·</span>Groq</div>
    <div class="ir-pill-warn"><span class="ir-dot" style="background:#d9a514;"></span>Educational only · Not financial advice</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="ir-side-label">Session</div>', unsafe_allow_html=True)
    if st.session_state.current_ticker:
        st.markdown(f'<div style="font:600 20px \'IBM Plex Mono\',monospace;">{st.session_state.current_ticker}</div>'
                    f'<div style="font-size:11px; color:var(--mut);">currently analysed</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:12.5px; color:var(--mut);">No stock analysed yet</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="ir-side-label">Data sources</div>', unsafe_allow_html=True)
    for name, note in [("SEC EDGAR", "filings"), ("yfinance", "market data"), ("News feed", "sentiment")]:
        st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:12.5px;margin:5px 0;">'
                    f'<span><span class="ir-dot" style="background:var(--pos);margin-right:8px;"></span>{name}</span>'
                    f'<span class="mono" style="color:var(--mut);font-size:10.5px;">{note}</span></div>', unsafe_allow_html=True)
    # ── API quota meters ──
    st.divider()
    st.markdown('<div class="ir-side-label">API quota</div>', unsafe_allow_html=True)
    g = USAGE.get("groq", {})
    if g.get("remaining_tokens") is not None and g.get("limit_tokens"):
        fig = usage_bar(g["remaining_tokens"], g["limit_tokens"], "Groq tokens/min")
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        reset = g.get("reset")
        if reset:
            st.markdown(f'<div style="font-size:10.5px;color:var(--fnt);margin-top:-6px;">resets in {reset}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:11.5px;color:var(--mut);">Groq: no calls yet</div>', unsafe_allow_html=True)
    gem = USAGE.get("gemini", {})
    if gem.get("used_requests", 0) > 0:
        st.markdown(f'<div style="font-size:11.5px;color:var(--mut);margin-top:6px;">Gemini fallback used: {gem["used_requests"]}x</div>', unsafe_allow_html=True)

    if st.session_state.last_run:
        st.divider()
        st.markdown('<div class="ir-side-label">Last run</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:12px;color:var(--mut);">{st.session_state.last_run}</div>', unsafe_allow_html=True)
    st.divider()
    if st.button("🔄  שיחה חדשה"):
        if st.session_state.agent:
            st.session_state.agent.reset()
        st.session_state.chat = []
        st.session_state.current_ticker = None
        st.session_state.last_run = None
        st.rerun()

if not _keys_present():
    st.error("לא נמצא מפתח API. הגדר GROQ_API_KEY ב-Streamlit Secrets כדי להפעיל את הסוכן.")
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# Render a structured report (charts + narrative) from a result dict
# ═════════════════════════════════════════════════════════════════════════════
def render_report(res):
    ticker = res["ticker"]
    market = res.get("market")
    metrics = res.get("metrics")
    technical = res.get("technical")
    news = res.get("news")
    peers_data = res.get("peers_data")

    # Header row
    price_str = f"${market.current_price}" if market and market.current_price else "—"
    st.markdown(f"""
    <div class="ir-rephead" style="margin-bottom:6px;">
      <div class="ir-repicon">{ticker[:2]}</div>
      <div><div style="font:600 22px 'IBM Plex Mono',monospace;">{ticker}</div>
      <div style="font-size:12.5px; color:var(--mut);">{res.get('asset_type','EQUITY').title()} · {price_str}</div></div>
    </div>""", unsafe_allow_html=True)

    # ETF / partial warning
    if res.get("warning"):
        st.markdown(f'<div class="ir-warn-banner">⚠️ {res["warning"].replace("⚠️ ","")}</div>', unsafe_allow_html=True)

    # Snapshot tiles
    tiles = snapshot_metrics(market)
    if tiles:
        cols = st.columns(len(tiles))
        for col, (label, value, delta) in zip(cols, tiles):
            col.metric(label, value, delta)

    # Price chart
    if market and market.price_history and market.price_dates:
        st.plotly_chart(
            price_chart(market.price_dates, market.price_history,
                        sma_20=technical.sma_20 if technical else None,
                        sma_50=technical.sma_50 if technical else None),
            use_container_width=True, key=f"price_{ticker}_{datetime.now().timestamp()}")

    # Technical + valuation row
    c1, c2 = st.columns(2)
    with c1:
        if technical and technical.rsi_14 is not None:
            st.plotly_chart(rsi_gauge(technical.rsi_14), use_container_width=True,
                            key=f"rsi_{ticker}_{datetime.now().timestamp()}")
    with c2:
        if metrics:
            rows = []
            for lbl, val in [("P/E", metrics.pe_ratio), ("P/B", metrics.pb_ratio),
                             ("P/S", metrics.ps_ratio), ("ROE", metrics.roe),
                             ("Net Margin", metrics.net_profit_margin)]:
                rows.append(f"| {lbl} | {val if val is not None else 'N/A'} |")
            st.markdown("**Valuation & Profitability**\n\n| Metric | Value |\n|---|---|\n" + "\n".join(rows))

    # Peer comparison bars
    if peers_data and len(peers_data) > 1:
        st.markdown("**Peer Comparison**")
        pc1, pc2 = st.columns(2)
        with pc1:
            fig = metrics_bar(ticker, peers_data, "pe_ratio", "P/E Ratio")
            if fig: st.plotly_chart(fig, use_container_width=True, key=f"pe_{ticker}_{datetime.now().timestamp()}")
        with pc2:
            fig = metrics_bar(ticker, peers_data, "net_profit_margin", "Net Margin")
            if fig: st.plotly_chart(fig, use_container_width=True, key=f"nm_{ticker}_{datetime.now().timestamp()}")

    # News sentiment
    if news and news.total_articles:
        sent_color = {"positive": "var(--pos)", "negative": "var(--neg)"}.get(news.overall_sentiment, "var(--mut)")
        themes = " · ".join(news.key_themes) if news.key_themes else "—"
        st.markdown(f'<div class="ir-card"><b>News &amp; Sentiment</b> &nbsp;'
                    f'<span style="color:{sent_color}; font-weight:600;">{news.overall_sentiment.title()}</span><br>'
                    f'<span style="font-size:12px; color:var(--mut);">{news.total_articles} articles · {themes}</span></div>',
                    unsafe_allow_html=True)

    # LLM narrative (Bull/Bear/Bottom line)
    st.markdown(res.get("narrative", ""))

    # Disclaimer
    st.caption("Disclaimer: Educational purposes only. Not financial advice.")


# ═════════════════════════════════════════════════════════════════════════════
# Replay chat history
# ═════════════════════════════════════════════════════════════════════════════
if not st.session_state.chat:
    st.markdown("""
    <div class="ir-welcome">
      <div style="font-size:38px; margin-bottom:10px;">📈</div>
      <div style="font-size:17px; font-weight:600;">שאל אותי על כל מניה אמריקאית</div>
      <div style="font-size:13px; color:var(--mut); margin-top:6px; direction:rtl;">
        כתוב בחופשיות בעברית או באנגלית, או לחץ על אחת הדוגמאות למטה.</div>
    </div>""", unsafe_allow_html=True)

    # Clickable example chips
    examples = [
        "תנתח את מניית פייסבוק",
        "תשווה בין Google ל-Meta",
        "איך אפל ביחס ל-QQQ?",
        "analyze Tesla",
        "תנתח את טבע",
        "השווה בין NVDA ל-AMD",
    ]
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        if cols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state.pending_input = ex
            st.rerun()
else:
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            if msg["kind"] == "report":
                render_report(msg["content"])
            else:
                st.markdown(msg["content"])

# ═════════════════════════════════════════════════════════════════════════════
# Chat input
# ═════════════════════════════════════════════════════════════════════════════
typed_input = st.chat_input("כתוב כאן... (לדוגמה: תנתח את אפל, או תשווה בין טבע לפייזר)")

# Use either a clicked example chip or typed text
user_input = st.session_state.pop("pending_input", None) or typed_input

if user_input:
    st.session_state.chat.append({"role": "user", "kind": "text", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    agent = get_agent()
    with st.chat_message("assistant"):
        with st.spinner("מבין את הבקשה..."):
            intent = parse_intent(agent.client, user_input, current_ticker=st.session_state.current_ticker)
        kind = intent.get("intent", "off_topic")

        if kind == "rate_limited":
            msg = "⏳ " + intent.get("message", "נגמרה מכסת ה-API הזמנית. נסה שוב בעוד מספר דקות.")
            st.markdown(f'<div class="ir-warn-banner">{msg}</div>', unsafe_allow_html=True)
            st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})

        elif kind in ("analyze", "compare") and intent.get("ticker"):
            ticker = intent["ticker"]
            peers = intent.get("peers", [])
            label = f"מנתח את {ticker}" + (f" מול {', '.join(peers)}" if peers else "") + "..."
            with st.spinner(label):
                res = analyse_structured(agent, ticker, peers=peers if peers else None)
            if res["ok"]:
                render_report(res)
                st.session_state.chat.append({"role": "assistant", "kind": "report", "content": res})
                st.session_state.current_ticker = ticker
                st.session_state.last_run = datetime.now().strftime("%b %d, %Y · %I:%M %p")
            else:
                st.markdown(f'<div class="ir-err-banner">{res["error"].replace("❌ ","")}</div>', unsafe_allow_html=True)
                st.session_state.chat.append({"role": "assistant", "kind": "text", "content": res["error"]})

        elif kind == "followup":
            if not st.session_state.current_ticker:
                msg = "עדיין לא ניתחנו מניה. נסה קודם: \"תנתח את אפל\"."
                st.markdown(msg)
                st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})
            else:
                with st.spinner("חושב..."):
                    answer = agent.follow_up(user_input)
                st.markdown(answer)
                st.session_state.chat.append({"role": "assistant", "kind": "text", "content": answer})

        elif kind in ("analyze", "compare"):
            msg = "לא הצלחתי לזהות מניה אמריקאית. נסה שם חברה או סימבול, לדוגמה: \"תנתח את Tesla\"."
            st.markdown(msg)
            st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})

        else:
            msg = "אני מתמחה במחקר מניות אמריקאיות בלבד. לדוגמה: \"תנתח את מיקרוסופט\"."
            st.markdown(msg)
            st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})

    st.rerun()
