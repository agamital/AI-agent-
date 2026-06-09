# Contributing Guide

This project is developed as a team-based Python AI Agents project.

The goal is to keep the project simple, modular, testable, and easy to review.

## Team Workflow

The main branch should contain stable code only.

After the initial setup, do not work directly on main.

For every task, create a feature branch.

Recommended workflow:

1. Pull the latest main branch.
2. Create a new feature branch.
3. Work only on the assigned task.
4. Run tests before pushing.
5. Commit with a clear message.
6. Push the branch to GitHub.
7. Open a Pull Request.

## Basic Git Commands

Start from main:

git checkout main

Pull latest changes:

git pull

Create a feature branch:

git checkout -b feature/task-name

Example:

git checkout -b feature/sec-tools

After making changes:

git status
git add .
git commit -m "Add SEC company facts tool skeleton"
git push -u origin feature/sec-tools

## Commit Guidelines

Use small and focused commits.

Good commit messages:

- Add SEC company facts tool skeleton
- Add technical indicator calculations
- Add ticker input validation
- Add Streamlit ticker input form
- Fix missing data handling in peer comparison

Bad commit messages:

- update
- fix
- changes
- final
- stuff

## Pull Request Rules

Before opening a Pull Request, run:

poetry run pytest -q

Also run:

poetry run ruff check .

A Pull Request should explain:

- What was changed
- Which files were changed
- How the change was tested
- Any known limitations

## Architecture Rules

Python tools should retrieve data, calculate metrics, validate inputs, or transform structured data.

Agents should use the LLM to interpret results, summarize findings, and generate structured reports.

The LLM should not invent financial numbers.

The LLM should not calculate financial metrics by itself.

Python calculates. LLM interprets and writes.

## Planned Tool Modules

Tools should be placed under:

src/investment_agent/tools/

Planned tools:

- sec_tools.py
- market_data_tools.py
- financial_metrics.py
- technical_indicators.py
- peer_comparison.py

## Planned Agent Modules

Agents should be placed under:

src/investment_agent/agents/

Planned agents:

- orchestrator.py
- fundamental_agent.py
- technical_agent.py
- report_agent.py
- factory.py

## Testing Rules

Every important calculation should have a test.

Early required tests:

- Financial metrics tests
- Technical indicator tests
- Ticker validation tests
- Report structure tests

Tests should be placed under:

tests/

## Data and Secrets Policy

Never commit:

- .env
- API keys
- Personal credentials
- Large raw data files
- Cache files
- Temporary outputs

Allowed in GitHub:

- .env.example
- README.md
- CONTRIBUTING.md
- pyproject.toml
- poetry.lock
- configs/
- src/
- scripts/
- tests/
- selected example reports

## Code Style

Use clear function names.

Keep functions small.

Prefer simple Python over unnecessary frameworks.

Use type hints where useful.

Write code comments in English.

Avoid duplicated code.

Keep configuration outside the code when possible.

## Communication Between Team Members

Before starting a task, define:

1. Which file you will edit.
2. Which function or module you will build.
3. What output is expected.
4. How the change will be tested.

Do not make large unrelated changes in one branch.
