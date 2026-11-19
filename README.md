# Label Hacker News job posts, four ways

Code from the Pydantic × Temporal webinar, 19 November 2026.

An agent built with [Pydantic AI](https://ai.pydantic.dev) reads each post in the November 2026 Hacker News "Who is
hiring?" thread and answers five questions about it. It runs on [Temporal](https://temporal.io), so stopping a worker
mid-run loses nothing. Each step changes one thing:

| Step | File | Who reads the posts |
|---|---|---|
| 1 | `step1_read_everything.py` | Sonnet |
| 2 | `step2_code_mode.py` | A script Sonnet writes, run in a Logfire Agent Sandbox |
| 3 | `step3_jev_reads.py` | Jev, a System One model, called from the script |
| 4 | `step4_jev_then_sonnet.py` | Jev, and Sonnet when Jev is unsure |

On the thread's first 50 posts:

| Step | Time | Cost | Right |
|---|---|---|---|
| 1 | 54 s | $0.21 | 48 / 50 |
| 2 | 40 s | $0.05 | 27 / 50 |
| 3 | 6 s | $0.01 | 45 / 50 |
| 4 | 7 s | $0.05 | 48 / 50 |

## Run

```bash
brew install temporal
uv sync
cp .env.example .env        # add your keys

temporal server start-dev   # UI at http://localhost:8233
uv run worker               # in a second terminal
uv run worker               # in a third: stop either mid-run and the other carries on
uv run label 1              # or 2, 3, 4
```

`src/hiring/plumbing/` holds the Temporal setup and the scoring against `data/answer_key.jsonl`.
