# Local Agent

Quick agent to prompt a model and call local tool modules (`build_tools`, `Db`, `Embeddings`, `test_tools`).

Setup

1. Copy `.env.example` to `.env` and set `GROQ_API_KEY` and `GROQ_API_URL`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Usage

- Start REPL:

```bash
python agent.py
```

- Run single ask:

```bash
python agent.py -c "ask Hello from Groq"
```

- Call local tool function:

```bash
python agent.py -c "call build_tools some_function [1,2,3]"
```

REPL commands
- `help` — show commands
- `modules` — list local modules and functions
- `call <module> <func> <json-args>` — invoke a function
- `ask <prompt>` — send prompt to model

Notes
- The script expects a Groq-compatible HTTP endpoint; set `GROQ_API_URL` in your `.env`.
- Adjust `MODULES` in `agent.py` if you have different filenames.
