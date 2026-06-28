# Progress Tracker

Status key: ⬜ not started | 🔄 in progress | ✅ done | ❌ blocked

---

## Week 1 — Foundation

### Days 1–2: Schemas + Tools + Error Handling

| Status | Task | File |
|---|---|---|
| ✅ | Data schemas (company, report) | `schemas/company.py`, `schemas/report.py` |
| ✅ | SEC EDGAR tool + retry | `tools/sec_tool.py` |
| ✅ | yfinance tool + retry | `tools/market_tool.py` |
| ✅ | Financial metrics calculator | `tools/metrics_tool.py` |
| ✅ | Technical indicators calculator | `tools/technical_tool.py` |
| ✅ | Peer comparison tool | `tools/peer_tool.py` |
| ✅ | Data validator | `validation/data_validator.py` |
| ✅ | Unit tests for all tools | `tests/test_tools.py` |

### Day 3: LLM Client + System Prompt

| Status | Task | File |
|---|---|---|
| ⬜ | Groq LLM client | `llm/groq_client.py` |
| ⬜ | System Prompt — all 6 components | `configs/prompts.yaml` |
| ⬜ | Config loader | `configs/config.py` |

### Day 4: Conversational Memory

| Status | Task | File |
|---|---|---|
| ⬜ | Conversation memory | `memory/conversation_memory.py` |
| ⬜ | Session store | `memory/session_store.py` |

### Days 5–7: Agents + Orchestrator + Graph

| Status | Task | File |
|---|---|---|
| ⬜ | Agent State definition | `agents/state.py` |
| ⬜ | Fundamental Analysis Agent | `agents/fundamental_agent.py` |
| ⬜ | Technical Analysis Agent | `agents/technical_agent.py` |
| ⬜ | Peer Comparison Agent | `agents/peer_agent.py` |
| ⬜ | Report Generation Agent | `agents/report_agent.py` |
| ⬜ | Orchestrator (Supervisor) | `agents/orchestrator.py` |
| ⬜ | LangGraph graph | `agents/graph.py` |
| ⬜ | CLI entry point | `scripts/run_agent.py` |
| ⬜ | Integration test | `tests/test_pipeline.py` |

---

## Week 2 — Intelligence + Deliverables

### Days 8–9: Agent Quality + Prompt Tuning

| Status | Task | File |
|---|---|---|
| ⬜ | Tune all agent prompts | `configs/prompts.yaml` |
| ⬜ | Improve missing data handling | `validation/data_validator.py` |
| ⬜ | End-to-end QA run (INTU + peers) | manual |

### Day 10: Streamlit UI

| Status | Task | File |
|---|---|---|
| ⬜ | Streamlit app | `app/streamlit_app.py` |

### Day 11: Usage Examples

| Status | Task | File |
|---|---|---|
| ⬜ | Example 1: AAPL standard analysis | `reports/examples/example_aapl.md` |
| ⬜ | Example 2: INTU + peers + follow-up | `reports/examples/example_intu_peers.md` |
| ⬜ | Example 3: Edge case / error | `reports/examples/example_edge_case.md` |

### Day 12: Reflection

| Status | Task | File |
|---|---|---|
| ⬜ | Reflection document | `reports/reflection.md` |

### Days 13–14: Final QA + Presentation

| Status | Task | Notes |
|---|---|---|
| ⬜ | All tests green | `poetry run pytest -q` |
| ⬜ | 3 clean pipeline runs | Demo reliability |
| ⬜ | Presentation prepared | 10 min: arch + demo + reflection |
| ⬜ | Files sent by email | hirshmanor@gmail.com |
| ⬜ | (Optional) MCP server | `mcp/sec_mcp_server.py` |

---

## Submission Checklist

- [ ] Code runs start to finish without errors
- [ ] At least 2 tools working
- [ ] System prompt contains all 6 components
- [ ] Conversational memory working
- [ ] Error handling with retry/fallback on all tools
- [ ] Streamlit UI working
- [ ] 3 documented usage examples
- [ ] Reflection document complete
- [ ] 10-minute presentation with live demo ready
- [ ] Files sent to hirshmanor@gmail.com

---

## Session Log

| Date | What was done |
|---|---|
| 2026-06-21 | Project planning completed. PLAN.md, PROGRESS.md, JOURNAL.md, CLAUDE.md created. |
| 2026-06-21 | All schemas written and verified: CompanyInfo, FinancialData, MarketData, MetricsResult, TechnicalIndicators, ResearchReport. Clean imports confirmed. |
| 2026-06-23 | All 5 tools written and tested against AAPL: sec_tool.py (3 functions), market_tool.py, metrics_tool.py, technical_tool.py, peer_tool.py. All return correct values. |
| 2026-06-24 | Data validator written and verified. 22 unit tests written and passing: validator (4), metrics math (5), technical math (7), SEC mocked (4), yfinance mocked (2). Days 1–2 complete. |
