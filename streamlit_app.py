"""
Investment Research Agent — Streamlit UI (hybrid)
Claude Design fintech styling + free-text Hebrew/English chat.

The user types naturally ("תנתח את פייסבוק", "compare Google with Meta",
"איך זה ביחס ל-QQQ"). An intent router decides whether to run a new
analysis, add a peer comparison, answer a follow-up, or decline off-topic.
"""

import os
import sys
from datetime import datetime

import streamlit as st

# ── Make the package importable locally and on Streamlit Cloud ───────────────
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from investment_agent.agents.research_agent import InvestmentResearchAgent
from investment_agent.agents.intent_router import parse_intent


# ═════════════════════════════════════════════════════════════════════════════
# Page config + Claude Design tokens
# ═════════════════════════════════════════════════════════════════════════════

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
.mono { font-family:'IBM Plex Mono', monospace; }

.stApp { background:#f4f4f7; }
.main .block-container { padding-top:1.2rem; max-width:1050px; }

/* Header */
.ir-header {
  display:flex; align-items:center; justify-content:space-between;
  background:#fff; border:1px solid var(--bd); border-radius:14px;
  padding:14px 22px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,.06);
}
.ir-logo {
  width:34px; height:34px; border-radius:9px; background:var(--acc);
  display:flex; align-items:center; justify-content:center;
  color:#fff; font:600 14px 'IBM Plex Mono',monospace;
  box-shadow:0 2px 8px rgba(88,73,240,.35);
}
.ir-title { font-size:15.5px; font-weight:600; }
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

/* Sidebar */
section[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--bd); }
.ir-side-label { font:600 10.5px 'IBM Plex Mono',monospace; letter-spacing:.1em;
  text-transform:uppercase; color:var(--fnt); margin:4px 0 8px; }

/* Report card — wraps the markdown report */
.ir-report {
  background:#fff; border:1px solid var(--bd); border-radius:14px;
  padding:8px 26px 20px; box-shadow:0 1px 3px rgba(0,0,0,.06); margin:6px 0;
}
.ir-report h1 { font-size:21px; margin-top:14px; }
.ir-report h2 { font-size:15.5px; margin-top:20px; color:#17171c; }
.ir-report table { width:100%; border-collapse:collapse; font-size:13px; margin:8px 0; }
.ir-report th { text-align:left; font:600 10px 'IBM Plex Mono',monospace;
  text-transform:uppercase; letter-spacing:.05em; color:var(--fnt);
  padding:6px 8px; border-bottom:1px solid var(--bd); }
.ir-report td { padding:8px; border-bottom:1px solid var(--bd); }
.ir-report blockquote {
  background:#fdf6e0; border-left:3px solid #d9a514; border-radius:6px;
  padding:10px 14px; margin:10px 0; color:#8a6a16; font-size:13px;
}

/* Welcome card */
.ir-welcome {
  background:#fff; border:1px solid var(--bd); border-radius:14px;
  padding:32px 28px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.06);
}
.ir-chip-row { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:14px; }
.ir-chip {
  font:500 12px 'IBM Plex Mono',monospace; padding:7px 13px; border-radius:8px;
  background:var(--accSoft); color:var(--acc); direction:rtl;
}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# Session state
# ═════════════════════════════════════════════════════════════════════════════

def _keys_present() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))

if "agent" not in st.session_state:
    st.session_state.agent = None
if "chat" not in st.session_state:
    st.session_state.chat = []          # list of dicts: {role, kind, content}
if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = None
if "last_run" not in st.session_state:
    st.session_state.last_run = None


def get_agent():
    if st.session_state.agent is None:
        st.session_state.agent = InvestmentResearchAgent()
    return st.session_state.agent


# ═════════════════════════════════════════════════════════════════════════════
# Header
# ═════════════════════════════════════════════════════════════════════════════

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
      Educational only · Not financial advice</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# Sidebar (Claude Design — data sources, current ticker, last run)
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<div class="ir-side-label">Session</div>', unsafe_allow_html=True)
    if st.session_state.current_ticker:
        st.markdown(
            f'<div style="font:600 20px \'IBM Plex Mono\',monospace; color:#17171c;">'
            f'{st.session_state.current_ticker}</div>'
            f'<div style="font-size:11px; color:var(--mut); margin-top:2px;">currently analysed</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="font-size:12.5px; color:var(--mut);">No stock analysed yet</div>',
                    unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="ir-side-label">Data sources</div>', unsafe_allow_html=True)
    for name, note in [("SEC EDGAR", "filings"), ("yfinance", "market data"), ("News feed", "sentiment")]:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:12.5px;margin:5px 0;">'
            f'<span><span class="ir-dot" style="background:var(--pos);margin-right:8px;"></span>{name}</span>'
            f'<span class="mono" style="color:var(--mut);font-size:10.5px;">{note}</span></div>',
            unsafe_allow_html=True,
        )

    if st.session_state.last_run:
        st.divider()
        st.markdown('<div class="ir-side-label">Last run</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:12px;color:var(--mut);">{st.session_state.last_run}</div>',
                    unsafe_allow_html=True)

    st.divider()
    if st.button("🔄  שיחה חדשה"):
        if st.session_state.agent:
            st.session_state.agent.reset()
        st.session_state.chat = []
        st.session_state.current_ticker = None
        st.session_state.last_run = None
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# No-keys guard
# ═════════════════════════════════════════════════════════════════════════════

if not _keys_present():
    st.error(
        "לא נמצא מפתח API. הגדר GROQ_API_KEY (ואופציונלית GEMINI_API_KEY) "
        "ב-Streamlit Secrets כדי להפעיל את הסוכן."
    )
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# Render chat history
# ═════════════════════════════════════════════════════════════════════════════

def render_message(msg):
    """Render one chat message by kind."""
    with st.chat_message(msg["role"]):
        if msg["kind"] == "report":
            st.markdown(f'<div class="ir-report">\n\n{msg["content"]}\n\n</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])


# Welcome state (only when no messages yet)
if not st.session_state.chat:
    st.markdown("""
    <div class="ir-welcome">
      <div style="font-size:38px; margin-bottom:10px;">📈</div>
      <div style="font-size:17px; font-weight:600; color:#17171c;">
        שאל אותי על כל מניה אמריקאית</div>
      <div style="font-size:13px; color:var(--mut); margin-top:6px; direction:rtl;">
        כתוב בחופשיות בעברית או באנגלית. הסוכן יבין, ימשוך נתונים אמיתיים מ-SEC,
        yfinance וחדשות, ויחזיר דוח מחקר מלא.</div>
      <div class="ir-chip-row">
        <span class="ir-chip">תנתח את מניית פייסבוק</span>
        <span class="ir-chip">תשווה בין Google ל-Meta</span>
        <span class="ir-chip">איך אפל ביחס ל-QQQ?</span>
        <span class="ir-chip">analyze Tesla</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.chat:
        render_message(msg)


# ═════════════════════════════════════════════════════════════════════════════
# Chat input + routing
# ═════════════════════════════════════════════════════════════════════════════

user_input = st.chat_input("כתוב כאן... (לדוגמה: תנתח את אפל, או תשווה בין טבע לפייזר)")

if user_input:
    # Show + store user message
    st.session_state.chat.append({"role": "user", "kind": "text", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    agent = get_agent()

    # Parse intent (with current ticker as context)
    with st.chat_message("assistant"):
        with st.spinner("מבין את הבקשה..."):
            intent = parse_intent(agent.client, user_input,
                                  current_ticker=st.session_state.current_ticker)

        kind = intent.get("intent", "off_topic")

        # ── analyze / compare → run a (new) analysis ─────────────────────────
        if kind in ("analyze", "compare") and intent.get("ticker"):
            ticker = intent["ticker"]
            peers = intent.get("peers", [])
            label = f"מנתח את {ticker}" + (f" מול {', '.join(peers)}" if peers else "") + "..."
            with st.spinner(label):
                report = agent.analyse(ticker, peers=peers if peers else None)

            st.markdown(f'<div class="ir-report">\n\n{report}\n\n</div>', unsafe_allow_html=True)
            st.session_state.chat.append({"role": "assistant", "kind": "report", "content": report})
            st.session_state.current_ticker = ticker
            st.session_state.last_run = datetime.now().strftime("%b %d, %Y · %I:%M %p")

        # ── followup → answer from memory ────────────────────────────────────
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

        # ── couldn't extract a ticker ────────────────────────────────────────
        elif kind in ("analyze", "compare"):
            msg = ("לא הצלחתי לזהות מניה אמריקאית בבקשה. "
                   "נסה שם חברה או סימבול, לדוגמה: \"תנתח את Tesla\" או \"NVDA\".")
            st.markdown(msg)
            st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})

        # ── off-topic ────────────────────────────────────────────────────────
        else:
            msg = ("אני מתמחה במחקר מניות אמריקאיות בלבד. "
                   "איך אוכל לעזור לך לנתח מניה? לדוגמה: \"תנתח את מיקרוסופט\".")
            st.markdown(msg)
            st.session_state.chat.append({"role": "assistant", "kind": "text", "content": msg})

    # Update sidebar (current ticker / last run)
    st.rerun()
