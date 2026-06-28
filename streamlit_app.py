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
    valuation_badge, rsi_badge, macd_badge, sma_badge, comparison_table_html, dynamic_comparison_html,
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
.ir-rephead { display:flex; align-items:center; gap:14px; }
.ir-repicon { width:48px; height:48px; border-radius:12px; background:var(--chip); display:flex; align-items:center; justify-content:center; font:600 16px 'IBM Plex Mono',monospace; }
.ir-metric-card { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:14px 18px; box-shadow:0 1px 3px rgba(0,0,0,.06); margin:6px 0; }
.ir-card-title { font-size:13px; font-weight:600; color:#17171c; margin-bottom:10px; }
.ir-table { width:100%; border-collapse:collapse; font-size:13px; }
.ir-table td { padding:8px 4px; border-bottom:1px solid var(--bd); }
.ir-table tr:last-child td { border-bottom:none; }
.ir-theme { display:inline-block; font-size:11px; padding:4px 9px; border-radius:7px; background:var(--chip); color:var(--mut); margin:0 4px 4px 0; }
.ir-narrative { background:#fff; border:1px solid var(--bd); border-radius:14px; padding:6px 20px 14px; box-shadow:0 1px 3px rgba(0,0,0,.06); margin:8px 0; }
.ir-narrative h2 { font-size:14.5px; margin-top:14px; }
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
    # ── API quota meter ──
    st.divider()
    st.markdown('<div class="ir-side-label">API quota</div>', unsafe_allow_html=True)
    g = USAGE.get("groq", {})
    shown = False
    if g.get("daily_limit"):
        rem = g.get("daily_remaining", 0)
        lim = g["daily_limit"]
        pct = rem / lim * 100 if lim else 0
        fig = usage_bar(rem, lim, "Groq tokens/day")
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        col = "var(--neg)" if pct < 20 else ("var(--mut)" if pct < 50 else "var(--pos)")
        lbl = f'<span style="color:{col};font-weight:600;">נשאר {rem:,} ({pct:.0f}%)</span>'
        if g.get("daily_reset"):
            lbl += f' <span style="color:var(--fnt);">· מתחדש בעוד {g["daily_reset"]}</span>'
        st.markdown(f'<div style="font-size:10.5px;margin-top:-6px;">{lbl}</div>', unsafe_allow_html=True)
        shown = True
    if g.get("remaining_tokens") is not None and g.get("limit_tokens"):
        fig = usage_bar(g["remaining_tokens"], g["limit_tokens"], "Groq tokens/min")
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if g.get("reset"):
            st.markdown(f'<div style="font-size:10.5px;color:var(--fnt);margin-top:-6px;">resets in {g["reset"]}</div>', unsafe_allow_html=True)
        shown = True
    if not shown:
        st.markdown('<div style="font-size:11.5px;color:var(--mut);">Groq: no calls yet</div>', unsafe_allow_html=True)
    gem = USAGE.get("gemini", {})
    if gem.get("used_requests", 0) > 0:
        st.markdown(f'<div style="font-size:11.5px;color:var(--mut);margin-top:6px;">Gemini fallback: {gem["used_requests"]}x</div>', unsafe_allow_html=True)

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


    # ── Report header ──
    price_str = f"${market.current_price}" if market and market.current_price else "—"
    delta_html = ""
    if market and market.current_price and market.previous_close:
        pct = (market.current_price - market.previous_close) / market.previous_close * 100
        dcol = "var(--pos)" if pct >= 0 else "var(--neg)"
        delta_html = f'<span style="color:{dcol};font:600 13px \'IBM Plex Mono\',monospace;">{pct:+.2f}%</span>'
    st.markdown(f"""
    <div class="ir-rephead" style="margin-bottom:10px;">
      <div class="ir-repicon">{ticker[:2]}</div>
      <div style="flex:1;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font:600 22px 'IBM Plex Mono',monospace;">{ticker}</span>
          <span style="font-size:11px;color:var(--mut);padding:2px 8px;border:1px solid var(--bd);border-radius:6px;">{res.get('asset_type','EQUITY').title()}</span>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font:600 22px 'IBM Plex Mono',monospace;">{price_str}</div>
        {delta_html}
      </div>
    </div>""", unsafe_allow_html=True)

    if res.get("warning"):
        st.markdown(f'<div class="ir-warn-banner">⚠️ {res["warning"].replace("⚠️ ","")}</div>', unsafe_allow_html=True)

    # ── Snapshot tiles ──
    tiles = snapshot_metrics(market)
    if tiles:
        cols = st.columns(len(tiles))
        for col, (label, value, delta) in zip(cols, tiles):
            col.metric(label, value, delta)

    # ── ETF-specific metrics card ──
    if market and getattr(market, "is_etf", False):
        etf_rows = []
        if market.etf_pe is not None:
            etf_rows.append(("Weighted P/E", f"{market.etf_pe:.1f}"))
        if market.etf_yield is not None:
            etf_rows.append(("Dividend Yield", f"{market.etf_yield*100:.2f}%"))
        if market.etf_3y_return is not None:
            etf_rows.append(("3-Year Avg Return", f"{market.etf_3y_return*100:.1f}%"))
        if market.etf_total_assets:
            aum = market.etf_total_assets
            aum_s = f"${aum/1e12:.2f}T" if aum >= 1e12 else f"${aum/1e9:.1f}B"
            etf_rows.append(("Total Assets (AUM)", aum_s))
        if market.etf_category:
            etf_rows.append(("Category", market.etf_category))
        if etf_rows:
            rows_html = "".join(
                f'<tr><td style="color:var(--mut);padding:8px 4px;">{l}</td>'
                f'<td style="text-align:right;font:500 13px \'IBM Plex Mono\',monospace;padding:8px 4px;">{v}</td></tr>'
                for l, v in etf_rows
            )
            st.markdown(f'''<div class="ir-metric-card">
              <div class="ir-card-title">📊 ETF Fund Metrics</div>
              <table class="ir-table">{rows_html}</table>
            </div>''', unsafe_allow_html=True)

    # ── Price chart ──
    if market and market.price_history and market.price_dates:
        st.plotly_chart(
            price_chart(market.price_dates, market.price_history,
                        sma_20=technical.sma_20 if technical else None,
                        sma_50=technical.sma_50 if technical else None),
            use_container_width=True, key=f"price_{ticker}_{datetime.now().timestamp()}")

    # ── Valuation + Technical cards (side by side) ──
    cur_price = market.current_price if market else None
    c1, c2 = st.columns(2)

    with c1:
        if metrics:
            rows_html = ""
            for lbl, val, key in [
                ("P/E", metrics.pe_ratio, "pe"), ("P/B", metrics.pb_ratio, "pb"),
                ("P/S", metrics.ps_ratio, "ps"), ("ROE", metrics.roe, "roe"),
                ("Net Margin", metrics.net_profit_margin, "margin"),
                ("Debt/Equity", metrics.debt_to_equity, "debt"),
            ]:
                vstr = f"{val:.2f}" if val is not None else "N/A"
                badge = valuation_badge(key, val)
                rows_html += (f'<tr><td style="color:var(--mut);">{lbl}</td>'
                              f'<td style="text-align:right;font:500 13px \'IBM Plex Mono\',monospace;">{vstr}</td>'
                              f'<td style="text-align:right;">{badge}</td></tr>')
            st.markdown(f'''<div class="ir-metric-card">
              <div class="ir-card-title">Valuation & Profitability</div>
              <table class="ir-table">{rows_html}</table></div>''', unsafe_allow_html=True)

    with c2:
        if technical:
            rows_html = ""
            for lbl, val, badge in [
                ("SMA-20", technical.sma_20, sma_badge(cur_price, technical.sma_20)),
                ("SMA-50", technical.sma_50, sma_badge(cur_price, technical.sma_50)),
                ("RSI-14", technical.rsi_14, rsi_badge(technical.rsi_14)),
                ("MACD", technical.macd_line, macd_badge(technical.macd_line, technical.macd_signal)),
            ]:
                vstr = f"{val:.2f}" if val is not None else "N/A"
                rows_html += (f'<tr><td style="color:var(--mut);">{lbl}</td>'
                              f'<td style="text-align:right;font:500 13px \'IBM Plex Mono\',monospace;">{vstr}</td>'
                              f'<td style="text-align:right;">{badge}</td></tr>')
            st.markdown(f'''<div class="ir-metric-card">
              <div class="ir-card-title">Technical Analysis</div>
              <table class="ir-table">{rows_html}</table></div>''', unsafe_allow_html=True)

    # ── Dynamic peer comparison (adapts to stock-vs-stock or ETF) ──
    comp = res.get("comparison")
    if comp:
        table = dynamic_comparison_html(comp, ticker)
        if table:
            st.markdown(table, unsafe_allow_html=True)
        # Visual P/E bar (works for both stocks and ETFs)
        if peers_data and len(peers_data) > 1:
            fig = metrics_bar(ticker, peers_data, "pe_ratio", "P/E Ratio (lower = cheaper)")
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"pe_{ticker}_{datetime.now().timestamp()}")

    # ── News sentiment ──
    if news and news.total_articles:
        sc = {"positive": "var(--pos)", "negative": "var(--neg)"}.get(news.overall_sentiment, "var(--mut)")
        sbg = {"positive": "var(--posSoft)", "negative": "var(--negSoft)"}.get(news.overall_sentiment, "var(--chip)")
        themes = "".join(f'<span class="ir-theme">{t}</span>' for t in (news.key_themes or [])[:4])
        st.markdown(f'''<div class="ir-metric-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="ir-card-title" style="margin:0;">News & Sentiment</span>
            <span style="background:{sbg};color:{sc};padding:4px 11px;border-radius:999px;font:600 11px 'IBM Plex Mono',monospace;">{news.overall_sentiment.title()}</span>
          </div>
          <div style="margin-top:8px;font-size:11px;color:var(--mut);">{news.total_articles} articles analysed</div>
          <div style="margin-top:8px;">{themes}</div>
        </div>''', unsafe_allow_html=True)

    # ── LLM narrative (Bull/Bear/Bottom line) ──
    st.markdown(f'<div class="ir-narrative">', unsafe_allow_html=True)
    st.markdown(res.get("narrative", ""))
    st.markdown('</div>', unsafe_allow_html=True)

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
        כתוב בחופשיות בעברית או באנגלית, או לחץ על אחת הדוגמאות.</div>
    </div>""", unsafe_allow_html=True)

    examples = [
        "תנתח את מניית פייסבוק",
        "תשווה בין Google ל-Meta",
        "איך אפל ביחס ל-QQQ?",
        "analyze Tesla",
        "תנתח את טבע",
        "השווה בין NVDA ל-AMD",
    ]
    ccols = st.columns(3)
    for i, ex in enumerate(examples):
        if ccols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
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
typed = st.chat_input("כתוב כאן... (לדוגמה: תנתח את אפל, או תשווה בין טבע לפייזר)")
user_input = st.session_state.pop("pending_input", None) or typed

if user_input:
    st.session_state.chat.append({"role": "user", "kind": "text", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    agent = get_agent()
    with st.chat_message("assistant"):
        with st.spinner("מבין את הבקשה..."):
            intent = parse_intent(agent.client, user_input, current_ticker=st.session_state.current_ticker)
        kind = intent.get("intent", "off_topic")

        if kind in ("analyze", "compare") and intent.get("ticker"):
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
