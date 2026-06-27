"""
Investment Research Agent — Streamlit UI
Design adapted from the Claude Design fintech mockup (IBM Plex, indigo accent,
green/red bull/bear, badge-driven tables).

Run locally:   streamlit run streamlit_app.py
Deploy:        share.streamlit.io  → point at this file
"""

import os
import sys
from datetime import datetime

import streamlit as st

# ── Make the package importable both locally and on Streamlit Cloud ──────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from investment_agent.agents.research_agent import InvestmentResearchAgent
from investment_agent.validation.ticker_validator import validate_ticker


# ─────────────────────────────────────────────────────────────────────────────
# Page config + design tokens (mirrors the mockup's CSS variables)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investment Research Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  --acc:#5849f0; --accSoft:#ecebfe;
  --pos:#0e9f6e; --posSoft:#e7f6ef;
  --neg:#e0342a; --negSoft:#fdeceb;
  --bd:#e9e9ee; --mut:#6c6c76; --fnt:#a2a2ac; --chip:#f1f1f4;
}

html, body, [class*="css"] { font-family:'IBM Plex Sans', sans-serif; }
code, .mono { font-family:'IBM Plex Mono', monospace; }

/* App background */
.stApp { background:#f4f4f7; }
.main .block-container { padding-top:1.4rem; max-width:1100px; }

/* Header band */
.ir-header {
  display:flex; align-items:center; justify-content:space-between;
  background:#fff; border:1px solid var(--bd); border-radius:14px;
  padding:15px 22px; margin-bottom:18px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);
}
.ir-logo {
  width:34px; height:34px; border-radius:9px; background:var(--acc);
  display:flex; align-items:center; justify-content:center;
  color:#fff; font:600 14px 'IBM Plex Mono',monospace;
  box-shadow:0 2px 8px rgba(88,73,240,.35);
}
.ir-title { font-size:15.5px; font-weight:600; letter-spacing:-0.01em; }
.ir-sub   { font-size:12px; color:var(--mut); margin-top:1px; }
.ir-pill {
  display:inline-flex; align-items:center; gap:6px; font-size:11px;
  color:var(--mut); padding:6px 11px; border:1px solid var(--bd);
  border-radius:999px; background:#fafafb;
}
.ir-pill-warn {
  display:inline-flex; align-items:center; gap:7px; font-size:11px;
  color:#9a7011; padding:6px 12px; border:1px solid #f1e3b8;
  border-radius:999px; background:#fdf6e0;
}
.ir-dot { width:6px; height:6px; border-radius:50%; display:inline-block; }

/* Section labels */
.ir-seclabel { display:flex; align-items:center; gap:9px; margin:6px 2px 10px; }
.ir-secnum   { font:600 11px 'IBM Plex Mono',monospace; color:var(--acc); letter-spacing:.06em; }
.ir-sectext  { font-size:14px; font-weight:600; }

/* Banners */
.ir-banner-warn {
  display:flex; gap:13px; padding:14px 18px; border-radius:12px;
  background:#fdf6e0; border:1px solid #f1e3b8; margin-bottom:16px;
}
.ir-banner-err {
  display:flex; gap:13px; padding:16px 18px; border-radius:12px;
  background:var(--negSoft); border:1px solid #f4c4c0; margin-bottom:16px;
}

/* Bull / Bear cards */
.ir-bull {
  border:1px solid var(--pos); border-radius:14px; padding:18px 20px;
  background:var(--posSoft);
}
.ir-bear {
  border:1px solid var(--neg); border-radius:14px; padding:18px 20px;
  background:var(--negSoft);
}
.ir-case-h { display:flex; align-items:center; gap:8px; margin-bottom:10px; font-size:14px; font-weight:700; }

/* Sidebar tweaks */
section[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--bd); }
.ir-side-label { font:600 10.5px 'IBM Plex Mono',monospace; letter-spacing:.1em;
  text-transform:uppercase; color:var(--fnt); margin-bottom:6px; }

/* Primary button */
.stButton > button {
  width:100%; height:44px; border:none; border-radius:10px;
  background:var(--acc); color:#fff; font-weight:600; font-size:14px;
  box-shadow:0 4px 14px rgba(88,73,240,.32);
}
.stButton > button:hover { background:#4a3cd8; color:#fff; }

/* Report markdown card */
.ir-report {
  background:#fff; border:1px solid var(--bd); border-radius:14px;
  padding:6px 24px 18px; box-shadow:0 1px 3px rgba(0,0,0,.06);
}
.ir-report h1 { font-size:22px; }
.ir-report h2 { font-size:16px; margin-top:18px; }
.ir-report table { font-size:13px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

if "agent" not in st.session_state:
    st.session_state.agent = None
if "report" not in st.session_state:
    st.session_state.report = None
if "chat" not in st.session_state:
    st.session_state.chat = []          # list of (role, text)
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None
if "run_meta" not in st.session_state:
    st.session_state.run_meta = None    # dict: time, warning


def _get_agent() -> InvestmentResearchAgent:
    """Lazily create the agent (keys must be in env)."""
    if st.session_state.agent is None:
        st.session_state.agent = InvestmentResearchAgent()
    return st.session_state.agent


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="ir-header">
  <div style="display:flex; align-items:center; gap:12px;">
    <div class="ir-logo">IR</div>
    <div>
      <div class="ir-title">Investment Research Agent</div>
      <div class="ir-sub">Autonomous equity research across SEC filings, market data &amp; news</div>
    </div>
  </div>
  <div style="display:flex; align-items:center; gap:9px;">
    <div class="ir-pill"><span class="mono" style="color:var(--acc); font-weight:600;">Llama 3.3 70B</span>
      <span style="color:var(--fnt);">·</span>Groq</div>
    <div class="ir-pill-warn"><span class="ir-dot" style="background:#d9a514;"></span>
      Educational use only · Not financial advice</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — inputs
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="ir-side-label">Analysis</div>', unsafe_allow_html=True)

    ticker = st.text_input("Ticker", value="AAPL", placeholder="e.g. AAPL").upper().strip()
    peers_raw = st.text_input(
        "Peer tickers · optional",
        value="MSFT, GOOGL",
        placeholder="MSFT, GOOGL",
    )
    st.caption("Comma-separated · up to 3 peers")

    run = st.button("↻  Run Analysis")
    st.caption("Supports U.S. stocks & ETFs only")

    st.divider()

    # Data sources status (static indicators — they reflect which tools exist)
    st.markdown('<div class="ir-side-label">Data sources</div>', unsafe_allow_html=True)
    for name, note in [
        ("SEC EDGAR", "filings"),
        ("yfinance", "market data"),
        ("News feed", "sentiment"),
    ]:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:12.5px;margin:4px 0;">'
            f'<span><span class="ir-dot" style="background:var(--pos);margin-right:8px;"></span>{name}</span>'
            f'<span class="mono" style="color:var(--mut);font-size:10.5px;">{note}</span></div>',
            unsafe_allow_html=True,
        )

    if st.session_state.run_meta:
        st.divider()
        st.markdown('<div class="ir-side-label">Last run</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:12px;color:var(--mut);">{st.session_state.run_meta["time"]}</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Run analysis
# ─────────────────────────────────────────────────────────────────────────────

def _keys_present() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))


if run:
    if not _keys_present():
        st.error(
            "No LLM API key found. Set GROQ_API_KEY (and optionally GEMINI_API_KEY) "
            "in Streamlit Secrets or your environment."
        )
    elif not ticker:
        st.warning("Please enter a ticker symbol.")
    else:
        # Pre-validate so we can show the design's warning/error banners
        validation = validate_ticker(ticker)

        if not validation["is_supported"]:
            st.markdown(f"""
            <div class="ir-banner-err">
              <div style="width:26px;height:26px;border-radius:7px;background:var(--neg);
                   color:#fff;display:flex;align-items:center;justify-content:center;
                   font-size:14px;font-weight:700;flex:none;">×</div>
              <div>
                <div style="font-size:13.5px;font-weight:700;color:var(--neg);">
                  Couldn't analyze "{ticker}"</div>
                <div style="font-size:12.5px;color:#9a3a34;line-height:1.45;margin-top:3px;">
                  {validation["message"].replace("❌ ", "")}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.session_state.report = None
        else:
            peers = [p.strip().upper() for p in peers_raw.split(",") if p.strip()]

            with st.spinner(f"Fetching data and generating report for {ticker}…"):
                agent = _get_agent()
                agent.reset()                       # fresh memory per run
                st.session_state.chat = []
                report = agent.analyse(ticker, peers=peers if peers else None)

            st.session_state.report = report
            st.session_state.last_ticker = ticker
            st.session_state.run_meta = {
                "time": datetime.now().strftime("%b %d, %Y · %I:%M %p"),
                "warning": validation.get("warning", ""),
            }


# ─────────────────────────────────────────────────────────────────────────────
# Report display
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.report:
    meta = st.session_state.run_meta or {}

    # ETF / partial-data warning banner
    if meta.get("warning"):
        st.markdown(f"""
        <div class="ir-banner-warn">
          <div style="width:26px;height:26px;border-radius:7px;background:#d9a514;
               color:#fff;display:flex;align-items:center;justify-content:center;
               font-size:15px;flex:none;">!</div>
          <div style="font-size:12.5px;color:#8a6a16;line-height:1.45;">
            {meta["warning"].replace("⚠️ ", "")}</div>
        </div>
        """, unsafe_allow_html=True)

    # The agent already returns a markdown banner line at the top sometimes;
    # render the whole report inside the styled card.
    st.markdown('<div class="ir-report">', unsafe_allow_html=True)
    st.markdown(st.session_state.report)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Follow-up chat ───────────────────────────────────────────────────────
    st.markdown(
        '<div class="ir-seclabel"><span class="ir-secnum">08</span>'
        '<span class="ir-sectext">Follow-up</span></div>',
        unsafe_allow_html=True,
    )

    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(text)

    question = st.chat_input(
        f"Ask a follow-up about {st.session_state.last_ticker}… "
        "(e.g. \"What is the RSI telling us?\")"
    )
    if question:
        st.session_state.chat.append(("user", question))
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                answer = _get_agent().follow_up(question)
            st.markdown(answer)
        st.session_state.chat.append(("assistant", answer))

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:var(--mut);">
      <div style="font-size:40px; margin-bottom:12px;">📈</div>
      <div style="font-size:16px; font-weight:600; color:#17171c;">
        Enter a ticker to generate a research report</div>
      <div style="font-size:13px; margin-top:6px;">
        Try AAPL, NVDA, TEVA, or an ETF like SPY. Add peers to compare side by side.</div>
    </div>
    """, unsafe_allow_html=True)

