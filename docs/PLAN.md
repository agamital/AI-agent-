# Investment Research Agent — Project Plan

## Architecture

```
User: "Analyze INTU, peers: ADBE CRM NOW"
              │
              ▼
   ┌──────────────────────┐
   │    ORCHESTRATOR      │  ← LLM supervisor. Reads the task,
   │  (Supervisor Agent)  │    decides which agents to call,
   │  + Conversation      │    maintains conversation history.
   │    Memory            │
   └──┬───────┬───────────┘
      │       │  (called as needed, in any order)
      ▼       ▼
 ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐
 │  Fund.  │ │Technical │ │   Peer     │ │  Report  │
 │Analysis │ │Analysis  │ │ Comparison │ │Generation│
 │  Agent  │ │  Agent   │ │   Agent    │ │  Agent   │
 └────┬────┘ └────┬─────┘ └─────┬──────┘ └────┬─────┘
      │           │              │              │
      └───────────┴──────────────┴──────────────┘
                        │
               Each agent calls tools
               autonomously as needed
                        │
     ┌──────────────────────────────────┐
     │  TOOLS  (pure Python)            │
     │  • SEC EDGAR tool                │
     │  • yfinance tool                 │
     │  • Financial metrics calculator  │
     │  • Technical indicators calc     │
     │  • Peer comparison tool          │
     └──────────────────────────────────┘
```

### Key Architecture Principles
- Python tools retrieve data and calculate metrics — no LLM involvement
- LLM agents interpret results and generate text — no raw number invention
- If data is missing → report it clearly, never let the LLM fill the gap
- Error handling lives inside every tool (retry + fallback), not as an afterthought

---

## Week 1 — Foundation

### Days 1–2: Schemas + Tools + Error Handling

| Task | File | Purpose |
|---|---|---|
| Data schemas | `schemas/company.py`, `schemas/report.py` | Pydantic models for all inputs/outputs |
| SEC EDGAR tool | `tools/sec_tool.py` | Fetch revenue, EPS, assets from SEC API. Returns None + logs on failure. (Retry on transient HTTP errors still TODO — see JOURNAL.) |
| yfinance tool | `tools/market_tool.py` | Historical prices, current quote. Returns None + logs on failure. (Retry/fallback still TODO — see JOURNAL.) |
| Financial metrics calculator | `tools/metrics_tool.py` | P/E, P/B, P/S, ROE, ROA, debt/equity, net + operating margins |
| Technical indicators calculator | `tools/technical_tool.py` | SMA, EMA, RSI, MACD |
| Peer comparison tool | `tools/peer_tool.py` | Side-by-side metrics table across tickers |
| Data validator | `validation/data_validator.py` | Flags missing fields clearly — never let LLM fill gaps |
| Unit tests for all tools | `tests/test_tools.py` | Test with AAPL. Test missing-data path too |

### Day 3: LLM Client + System Prompt

| Task | File | Purpose |
|---|---|---|
| Groq LLM client | `llm/groq_client.py` | Thin wrapper: send messages → get response, with retry on rate limit |
| System Prompt (6 components) | `configs/prompts.yaml` | One structured prompt per agent — all 6 required components |
| Config loader | `configs/config.py` | Load model name, temperature, API keys from .env |

**Required 6 system prompt components per agent:**
- Persona — who is the agent, what is its expertise
- Goal — what it must achieve
- Tools — what tools it has and when to use each
- Process — step-by-step process to follow
- Constraints — what it is forbidden from doing
- Output Format — exact structure of its response

### Day 4: Conversational Memory

| Task | File | Purpose |
|---|---|---|
| Conversation memory | `memory/conversation_memory.py` | Wraps LangGraph MessagesState — stores full message history for follow-up questions |
| Session store | `memory/session_store.py` | In-memory dict keyed by session ID |

**What this enables:**
```
Turn 1 → "Analyze AAPL"          → runs full pipeline, stores in memory
Turn 2 → "Now compare with MSFT" → recalls AAPL, only fetches MSFT
Turn 3 → "What was AAPL's P/E?"  → answers from memory, no API call
```

### Days 5–7: Agents + Orchestrator + LangGraph Graph

| Task | File | Purpose |
|---|---|---|
| Agent State | `agents/state.py` | TypedDict: ticker, peers, messages, fetched_data, analyses, report, errors |
| Fundamental Analysis Agent | `agents/fundamental_agent.py` | ReAct loop: calls SEC + metrics tools, returns structured analysis |
| Technical Analysis Agent | `agents/technical_agent.py` | ReAct loop: calls market + technical tools, returns indicators analysis |
| Peer Comparison Agent | `agents/peer_agent.py` | Calls peer tool, compares metrics across tickers |
| Report Generation Agent | `agents/report_agent.py` | Takes all analyses, generates final Markdown report |
| Orchestrator (Supervisor) | `agents/orchestrator.py` | LangGraph supervisor: routes to agents, collects results, uses memory |
| LangGraph graph | `agents/graph.py` | Wires all agents into one compiled StateGraph |
| CLI entry point | `scripts/run_agent.py` | `--ticker INTU --peers ADBE CRM NOW` → saves report to /reports/ |
| Integration test | `tests/test_pipeline.py` | Full pipeline on AAPL. Also: bad ticker, missing data, follow-up question |

---

## Week 2 — Intelligence + Deliverables

### Days 8–9: Agent Quality + Prompt Tuning

| Task | File | Purpose |
|---|---|---|
| Tune fundamental prompts | `configs/prompts.yaml` | Better P/E, ROE, debt interpretation with sector context |
| Tune technical prompts | `configs/prompts.yaml` | RSI > 70 = overbought, MACD crossover interpretation |
| Tune peer comparison prompts | `configs/prompts.yaml` | Highlight relative outperformance, not just list numbers |
| Improve missing data handling | `validation/data_validator.py` | Every missing field → clear human-readable note in report |
| End-to-end QA run | manual | Run INTU + ADBE CRM NOW. Fix anything broken in real conditions |

### Day 10: Streamlit UI

| Task | File | Purpose |
|---|---|---|
| Streamlit app | `app/streamlit_app.py` | Input: ticker + peers. Button: Run Analysis. Output: rendered report. Shows conversation history. User-friendly error messages |

### Day 11: 3 Usage Examples

| Task | File | What it covers |
|---|---|---|
| Example 1: Standard analysis | `reports/examples/example_aapl.md` | AAPL solo — happy path, all data available |
| Example 2: Multi-peer comparison | `reports/examples/example_intu_peers.md` | INTU vs ADBE CRM NOW + conversational follow-up |
| Example 3: Edge case | `reports/examples/example_edge_case.md` | Bad ticker or missing SEC data — tests error handling |

Each example: **Input → Full Output → Explanation of what the agent did and why**

### Day 12: Reflection Document

| Task | File | Content |
|---|---|---|
| Reflection | `reports/reflection.md` | All required reflection questions answered |

**Reflection questions to cover:**
- What does the agent do? (project description)
- What tools did you use and why?
- What worked well?
- What was challenging?
- Where does the agent get stuck?
- How did you handle errors?
- What surprised you?
- If you started over, what would you do differently?

### Days 13–14: Final QA + Presentation

| Task | Purpose |
|---|---|
| All tests green (`poetry run pytest -q`) | No broken tools before submission |
| Run full pipeline 3 times cleanly | Confirm demo reliability |
| Presentation structure (10 min) | 2 min: problem + architecture. 5 min: live demo. 3 min: reflection |
| Email submission | Code + examples + reflection to hirshmanor@gmail.com |
| (Optional) MCP server | `mcp/sec_mcp_server.py` — only if everything else is solid |

---

## Build Order (Critical Path)

```
Schemas → Tools (with error handling) → Tests → System Prompts → Groq client
→ Conversational Memory → Agents (ReAct) → Orchestrator → Graph → CLI
→ Streamlit UI → Usage Examples → Reflection → Presentation
```

---

## Submission Checklist

- [ ] Code runs start to finish without errors
- [ ] At least 2 tools working (we have 5)
- [ ] System prompt contains all 6 components (Persona, Goal, Tools, Process, Constraints, Output Format)
- [ ] Conversational memory working
- [ ] Error handling with retry/fallback on all tools
- [ ] Streamlit UI working
- [ ] 3 documented usage examples (input + output + explanation)
- [ ] Reflection document complete
- [ ] 10-minute presentation with live demo ready
- [ ] Files sent to hirshmanor@gmail.com
