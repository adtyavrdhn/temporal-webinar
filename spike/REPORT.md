# HN "Who is hiring?" demo spike: does the Jev + Code Mode arc hold?

**Status (17 Nov 2026): blocked on keys.** No model was called, so none of the four agent setups, the Jev classifier or
the LLM classifier has been run, and there are no token, cost or trace numbers. What did run: the data cache, the
answer key, and two keyword classifiers scored against the key. Every number below was measured. Nothing is estimated.

## Keys

Checked by name only (values never printed):

| Variable | Present |
|---|---|
| `TYPESAFE_API_KEY` | **missing** |
| `OPENAI_API_KEY` | **missing** |
| `ANTHROPIC_API_KEY` | **missing** |
| `PYDANTIC_AI_GATEWAY_API_KEY` | **missing** |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | missing (also checked) |
| `LOGFIRE_TOKEN` | missing |
| `LOGFIRE_API_KEY` | missing |

To unblock: `TYPESAFE_API_KEY` plus one LLM key (gateway, OpenAI or Anthropic). Add `LOGFIRE_TOKEN` for traces, and
`LOGFIRE_API_KEY` with run-code permission for the remote sandbox. All of these go in the repository's env settings.
The DynamicWorkflow/Temporal smoke test also needs the `temporal` CLI, which isn't installed in this sandbox (or
temporalio's testing environment, which downloads a dev server on first use).

## What ran and what didn't

| Step | Status |
|---|---|
| uv project, Python 3.12, deps | done (`spike/pyproject.toml`, `uv.lock`) |
| Data: 12 threads cached | done (`data/posts_YYYY-MM.jsonl`, `data/threads.json`) |
| Answer key, 158 Nov 2026 posts, labelled by hand | done and frozen (`data/answer_key.jsonl`, sha256 in `data/answer_key.sha256`, checked by the evaluator) |
| Keyword classifiers vs key (naive, careful regex), 3 runs | done (`results/{naive,regex}_*.csv`) |
| Setup 1 plain tools, 2 CodeMode no Jev, 3 CodeMode + Jev, 4 + LLM second opinion | **not run**: no LLM / TypeSafe key |
| Jev and LLM per-field classifiers vs key | **not run**: no keys |
| Tokens, $ cost, model/tool calls, Logfire traces | **none**: nothing paid ran |
| 12-month run of setup 3/4 | **not run** |
| DynamicWorkflow + Jev sub-agent + CodeMode under TemporalDurability | **not run**: needs Jev and an LLM; no `temporal` CLI here |

## Setup and API notes

- Installed: pydantic-ai-slim 2.69.0, pydantic-ai-harness 0.69.0, logfire 5.6.0, pydantic-monty 1.6.0,
  temporalio 1.36.1, typesafe-sdk 0.7.5. `uv init` picked Python 3.14 by default. It's pinned to 3.12 with
  `.python-version` and `requires-python = ">=3.12,<3.13"`.
- These imports resolve: `TypeSafeModel`, `BoolCriteria`, `UseEnumMemberDocstrings`, `CodeMode`, `DynamicWorkflow`,
  `TemporalDurability` / `PydanticAIPlugin` / `PydanticAIWorkflow`, `logfire.agent_sandboxes`.
- Docs read: pydantic-ai `docs/models/decision.md`, `docs/models/typesafe.md`, `docs/harness/code-mode.md`,
  `docs/harness/dynamic-workflow.md` (main branch). Where they differ from, or add to, the brief:
  - **Confidence** is in `result.response.provider_details['confidence']` as one number per field (e.g.
    `{'remote': 0.81, 'ai_role': 0.24}`). It's a *margin* from the decision threshold, not the probability of being
    right: a bool at p=0.45 reports 0.10. `float` fields get no confidence. Pick-one fields report it differently
    from bools, so setup 4 needs **one bar per field**, tuned on the key.
  - **Setup 4 has a built-in path**: `ModelFallback(fallback_on=<handler that reads the confidence>)` hands
    low-confidence responses to an LLM (decision.md "Falling back on low confidence"). That's an alternative to
    calling the LLM by hand from the script.
  - **Jev limit: 32k tokens** for the state plus the longest question (jev-1.13). One post (median ~1.1k chars) fits.
    A whole month (~68k tokens) does not, so one call per post is required, not just preferred.
  - Questions go on the output type: model docstring = goal, field docstring = question, `BoolCriteria(true=, false=)`
    for boundary cases. TypeSafe say to ask one thing per field, and that Jev reads literally. That matters for
    `open_to_eu_remote`, which hides two judgements (is it remote, and does the region include the EU). It may be
    better to ask Jev for remote + region and derive the EU flag in Python.
  - Pin the model once a threshold is tuned: `jev-latest` moves. `ModelResponse.model_name` reports the versioned id.
  - CodeMode: `CodeMode(monty_sandbox=logfire.agent_sandboxes)` takes the function, not a call. Under Temporal,
    `run_code` runs as workflow code and is replayed. Nested tool calls are activities. The 2-second workflow-task
    limit means heavy compute belongs in a tool.
  - DynamicWorkflow: sub-agents are called as `await name(task=...)` from a Monty script, with `asyncio.gather`
    fan-out. Structured sub-agent output comes back as a dict. `max_agent_calls` defaults to **50**, so a 150-post
    fan-out needs it raised. Under Temporal: `TemporalDurability` on the orchestrator *and* on each sub-agent, each
    registered with its own `AgentPlugin`.

## Data

Source: HN Algolia API, top-level comments only (`parent_id == story id`), HTML stripped and unescaped
(`fetch_data.py`). The Nov 2026 count (245) matches the earlier probe.

| Month | Story id | Top-level posts |
|---|---|---|
| 2025-12 | 46108941 | 378 |
| 2026-01 | 46466074 | 255 |
| 2026-02 | 46857488 | 410 |
| 2026-03 | 47219668 | 315 |
| 2026-04 | 47601859 | 326 |
| 2026-05 | 47975571 | 317 |
| 2026-06 | 48357725 | 312 |
| 2026-07 | 48747976 | 255 |
| 2026-08 | 49156683 | 223 |
| 2026-09 | 49522897 | 247 |
| 2026-10 | 49922569 | 253 |
| 2026-11 | 50338728 | 245 |

## Answer key

**Sample** (`select_sample.py`, seed 20261117, deterministic: re-running it gives a byte-identical file). Each Nov post
goes into the first trap stratum it matches. Strata of 12 or fewer posts are taken whole, the rest at 150/245. The
weight N/n on each post extrapolates the key to the full month.

| Stratum | Posts in month | Sampled | Weight |
|---|---|---|---|
| no_pipe_header | 27 | 17 | 1.588 |
| seeking_or_location | 4 | 4 | 1.000 |
| remote_restricted (remote + region word in header) | 83 | 51 | 1.627 |
| funding_money (funding/revenue word + money figure) | 31 | 19 | 1.632 |
| odd_pay (hourly/monthly/non-USD) | 12 | 12 | 1.000 |
| ai_header | 24 | 15 | 1.600 |
| ai_blurb_only (AI only in the body) | 39 | 24 | 1.625 |
| multi_role | 3 | 3 | 1.000 |
| other | 22 | 13 | 1.692 |
| **total** | **245** | **158** | |

**Labelling rules.** I read every post myself (no model calls) and applied these:

- `is_job`: the post offers paid or equity work. Job seekers, ads, "." and non-job programs are false. Expired posts,
  recruiter posts, commission-only and equity-only roles count as jobs.
- `remote`: `anywhere` = remote with no region, or only a soft preference ("US/EU timezones preferred").
  `restricted` = remote limited by country, region **or required working hours**. `onsite_or_hybrid` = no remote
  option (a location with no remote mention counts here). `unclear` = no location, or not a job. A multi-role post
  takes its most permissive option.
- `open_to_eu_remote`: someone living in an EU country can take it remotely. UK-only and US-only are false. An
  hours requirement an EU resident can meet (e.g. 4h overlap with US East) is true.
- `ai_role`: a listed role's title is AI/ML, or the role's main work is building AI/ML/LLM/agent systems. AI in the
  company blurb, "use AI tools", or one agent bullet among several doesn't count. A multi-role post is true if any
  listed role is AI/ML.
- `salary_listed`: a pay figure for the role (yearly, hourly, monthly, stipend, any currency). Funding, revenue,
  market size, signing bonuses, "competitive", "by agreement" and placeholders (`[salary range]`, `$XXX/hour`) are
  false.

**Counts in the key (158 posts):** 145 jobs / 13 not. remote: 65 onsite_or_hybrid, 60 restricted, 18 anywhere,
15 unclear. 46 open to EU remote, 37 AI roles, 52 with salary listed. **43 marked ambiguous.**
Full-month extrapolation of the headline (job and open to EU remote) for Nov 2026: **70.5** of 245.

### Ambiguous labels, for your review

| Post id | Header (trimmed) | Label | Why it's hard |
|---|---|---|---|
| 50338768 | University of Cambridge, University of Manchester / PhD in AI / Earth | job, onsite_or_hybrid, eu=F, ai=T, sal=T | Funded PhD studentship counted as a job; GBP 30k stipend counted as salary. |
| 50338809 | UPDATE (Nov 13): We're no longer taking applications for these roles. | job, restricted, eu=F, ai=T, sal=T | Applications closed but still a job post; pipe header is on line 3. |
| 50339364 | CoVar / Durham, NC and McLean, VA / ... / HYBRID | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Jack-of-all-trades incl. prototyping CV algorithms; counted not an AI role. |
| 50339383 | Tandem Health / Engineers, Designers, PMs / On-site in Stockholm | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Generic roles at an AI company; $100M Series B is funding. |
| 50339975 | humans& / Product Engineer (Member of Technical Staff) / San Francisco | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Product engineer on an AI assistant's UX, not the model. |
| 50340449 | Mesmer (YC P25) / Founding Engineer / Berlin / ONSITE | job, onsite_or_hybrid, eu=F, ai=F, sal=T | Uses coding agents for customers; not building AI/ML. |
| 50340480 | AI x Healthcare Startup / bracehealth.com / Boston, MA Onsite | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Full-stack "at the edge of LLMs and agentic systems"; $5T is market size. |
| 50340958 | Jump / Founding Engineers (Software/AI, Manufacturing) / Miami | job, onsite_or_hybrid, eu=F, ai=T, sal=T | Remote (US) only until Jan 2027, then onsite -> onsite_or_hybrid. |
| 50341824 | eventfirst / Senior Full-Stack Engineer / Berlin / REMOTE (CET) | job, restricted, eu=T, ai=F, sal=F | Full-stack wanting AI chat product experience; counted not an AI role. |
| 50342041 | ArtCraft / Senior Engineers / SF (Onsite) / Atlanta (Onsite) | job, onsite_or_hybrid, eu=F, ai=F, sal=T | "agent workflows" among product areas; "eight figures run rate" is revenue. |
| 50342797 | Curiosity / Forward Deployed Engineer, DevOps Architect / Toulouse | job, onsite_or_hybrid, eu=F, ai=F, sal=F | FDE also "ships agents on top". |
| 50342990 | Middesk / SF / NYC / Hybrid | job, onsite_or_hybrid, eu=F, ai=F, sal=T | Data Scientist roles not counted as AI/ML. |
| 50343048 | Rootly / engineering, GTM, product, sales / SF Bay, Toronto, APAC, Remote | job, anywhere, eu=T, ai=F, sal=F | "Remote" listed among locations with no region. |
| 50343546 | Subimage (YC W25) / Founding Engineer / San Francisco / ONSITE | job, onsite_or_hybrid, eu=F, ai=F, sal=T | Some listed problems involve the product's agent. |
| 50344341 | StudyTurtle (no pipe header) | job, restricted, eu=T, ai=F, sal=F | Remote non-US with PST overlap; EU possible but late hours. |
| 50344773 | yeet / Chicago, IL / Remote / Full-Time | job, anywhere, eu=T, ai=F, sal=F | "Chicago / Remote" with no region. |
| 50345264 | Beacon AI / 3 days hybrid in San Carlos, CA | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Lead Autonomy/Robotics role not counted as AI. |
| 50346665 | Telescope Partners / Software Engineer & Data Scientist / Remote - AMERICAS ONLY | job, restricted, eu=F, ai=F, sal=F | Team automates investor tasks with agents. |
| 50347792 | KSC Trading / Remote or NYC Hybrid | job, restricted, eu=T, ai=F, sal=T | Job with a "Location:" line; remote with 4h US-East overlap -> restricted, EU can meet it. |
| 50348145 | VALIS / Software Engineer / REMOTE (US, East Coast hours) | job, restricted, eu=F, ai=F, sal=T | Agentic features are one of three bullets. |
| 50349000 | Blockrotate / Senior Systems / Rust Engineer / Remote (US/EU timezones preferred) | job, anywhere, eu=T, ai=F, sal=T | "preferred" read as a preference, not a restriction. |
| 50351266 | AREO / Remote (EU) and On-Site in Bremen | job, restricted, eu=T, ai=T, sal=F | Robotics engineer (VLAs, autonomous models) counted as AI. |
| 50351346 | ProphetX / Multiple Roles / REMOTE (US) | job, restricted, eu=T, ai=F, sal=F | One role "should be open for EU timezones". |
| 50351794 | Taxnova / London / Hybrid | job, onsite_or_hybrid, eu=F, ai=T, sal=F | Founding engineer owns "the AI product". |
| 50352937 | TheraPlug / Founding CTO / Detroit preferred; remote considered | job, unclear, eu=F, ai=F, sal=F | Remote considered with no region; pre-funding, no salary. |
| 50353464 | DigiKey / Search Experience Manager / MN / Hybrid | job, onsite_or_hybrid, eu=F, ai=F, sal=F | Owns search incl. AI/LLMs; counted not an AI role. |
| 50354142 | Exponent / Lead Engineer, AI Accounting / New York / HYBRID | job, onsite_or_hybrid, eu=F, ai=T, sal=T | Backend-focused but owns LLM classification behaviour. |
| 50360244 | Coder / Multiple roles / Multiple locations | job, restricted, eu=T, ai=T, sal=F | Agentic Engineering / AI Governance roles counted as AI; EU roles in Ireland/Poland. |
| 50361229 | Lumen Labs / Robotics/Hardware Engineer, Simulation Engineer / SF | job, onsite_or_hybrid, eu=F, ai=F, sal=T | Robotics/simulation for policy training. |
| 50363483 | Bubblehouse / Fully REMOTE / $200-250k | job, restricted, eu=T, ai=F, sal=T | 9am-noon NY hours required -> restricted; EU feasible. |
| 50365279 | Search Atlas / REMOTE (anywhere, EST hours) / $23-34/hr | job, restricted, eu=T, ai=F, sal=T | "anywhere" but EST hours -> restricted by hours. |
| 50370710 | Kaida / Remote | not job | Contributors / founding team for a solo project. |
| 50380439 | ChainSecurity / HYBRID/REMOTE, Zurich | job, anywhere, eu=T, ai=F, sal=F | Remote with no region. |
| 50393239 | Machine Age / COO / UK time zone / Salary post-raise | job, restricted, eu=T, ai=F, sal=F | No location; "work UK hours" read as remote restricted by hours. |
| 50420399 | OpenTrain AI / REMOTE (US) / Backend Engineer, AI Coding Task Design | job, restricted, eu=F, ai=T, sal=T | Designs coding tasks/verifiers for AI training: counted as AI. |
| 50447035 | Odin / Senior Cloud Infra Engineer / Remote | job, anywhere, eu=T, ai=F, sal=F | "Remote" with no region. |
| 50449027 | Nevral Forensics Intelligence / Research Partner Program / REMOTE (worldwide) | not job | Says itself it isn't a job posting. |
| 50451710 | RAIDS AI / Senior Technical Project Manager / REMOTE | job, anywhere, eu=T, ai=F, sal=F | Cyprus company; TPM over AI researchers counted not an AI role. |
| 50466168 | Native / Founding Builder-in-Residence / SF or London / REMOTE or ONSITE | job, anywhere, eu=T, ai=F, sal=T | No region; monthly contract pay. |
| 50479794 | Location: REMOTE (anywhere) / 50% rev share | not job | Rev-share partnership for a video editor. |
| 50481529 | Elm AI / Forward-Deployed Product Engineer / REMOTE US/Europe considered | job, restricted, eu=T, ai=F, sal=F | FDE at an AI agents company. |
| 50483905 | Bechtel / Penetration Tester / Remote or onsite (US + many countries) | job, restricted, eu=F, ai=F, sal=T | "many countries" unspecified -> EU not established; "<$145k". |
| 50508598 | New Product / Full Stack Engineer / Meet In The Bay Area / Work Remotely | job, restricted, eu=F, ai=F, sal=F | "$XXX/hour" placeholder; must work at a Bay Area company. |

Changing a label means editing `answer_key.jsonl` and the `KEY_SHA` in `eval_classifier.py` together. The hash check
is there so the key can't drift quietly between runs.

## Results so far (keyword classifiers only)

Two code-only classifiers stand in for what a Code Mode script without Jev can do (`classifiers.py`):

- **naive**: the first script a model tends to write. Every post is a job, "remote" in the header means remote
  anywhere, AI/money keywords anywhere in the text.
- **regex (careful)**: header-based, checks for "SEEKING"/"Location:", region words after "remote", an EU word
  list, AI keywords only in the header, money figures anywhere. I wrote it *after* reading all the traps, so treat it
  as an upper bound on a keyword script, not a typical one.

Both are deterministic. Three runs gave identical results (wall time ~0.01 s per 158 posts, $0, no model calls).

### Per field vs the answer key (n=158)

| Classifier | Field | Accuracy | Precision | Recall |
|---|---|---|---|---|
| naive | is_job | 0.918 (145/158) | 0.918 (145/158) | 1.000 (145/145) |
| naive | remote | 0.519 (82/158) | n/a | n/a |
| naive | open_to_eu_remote | 0.741 (117/158) | 0.531 (43/81) | 0.935 (43/46) |
| naive | ai_role | 0.570 (90/158) | 0.352 (37/105) | 1.000 (37/37) |
| naive | salary_listed | 0.911 (144/158) | 0.788 (52/66) | 1.000 (52/52) |
| regex | is_job | 0.937 (148/158) | 0.986 (137/139) | 0.945 (137/145) |
| regex | remote | 0.867 (137/158) | n/a | n/a |
| regex | open_to_eu_remote | 0.930 (147/158) | 0.907 (39/43) | 0.848 (39/46) |
| regex | ai_role | 0.823 (130/158) | 0.636 (21/33) | 0.568 (21/37) |
| regex | salary_listed | 0.899 (142/158) | 0.781 (50/64) | 0.962 (50/52) |
| Jev | all | not run | | |
| LLM | all | not run | | |

### Headline count: "job posts remote and open to someone in the EU", Nov 2026

| Classifier | On the 158-post key: key / predicted / error | Full month: key extrapolation / predicted / error |
|---|---|---|
| naive | 46 / 81 / **+35** | 70.5 / 130 / **+59.5** |
| regex | 46 / 43 / **-3** (4 FP, 7 FN cancel) | 70.5 / 67 / **-3.5** |

The careful regex lands near the right count, but only because errors cancel: 11 posts are wrong, 9 of them on
labels marked ambiguous. Other questions on the same sample:

| Question (on the 158) | Key | naive predicted (posts wrong) | regex predicted (posts wrong) |
|---|---|---|---|
| AI roles | 37 | 105 (68) | 33 (28) |
| Salary listed | 52 | 66 (14) | 64 (16) |
| AI roles open to EU remote | 9 | 49 (42) | 10 (11) |
| Open to EU remote with salary | 12 | 28 (16) | 14 (4) |

### Monthly series (keyword classifiers; no key outside Nov)

| Month | Story id | Posts | naive: EU-remote jobs | regex: EU-remote jobs |
|---|---|---|---|---|
| 2025-12 | 46108941 | 378 | 198 | 113 |
| 2026-01 | 46466074 | 255 | 132 | 82 |
| 2026-02 | 46857488 | 410 | 206 | 124 |
| 2026-03 | 47219668 | 315 | 152 | 93 |
| 2026-04 | 47601859 | 326 | 156 | 100 |
| 2026-05 | 47975571 | 317 | 158 | 89 |
| 2026-06 | 48357725 | 312 | 144 | 71 |
| 2026-07 | 48747976 | 255 | 129 | 74 |
| 2026-08 | 49156683 | 223 | 100 | 60 |
| 2026-09 | 49522897 | 247 | 128 | 69 |
| 2026-10 | 49922569 | 253 | 131 | 73 |
| 2026-11 | 50338728 | 245 | 130 | 67 (key extrapolation: 70.5) |

### Traps: who got them right

Jev and LLM columns stay empty until those classifiers run.

| Trap | Post | Key | naive | regex |
|---|---|---|---|---|
| Remote restricted to a non-EU region | Juro, "REMOTE (UK)" | eu=F | eu=T ✗ | eu=F ✓ |
| Remote restricted to regions incl. EU | River, "REMOTE (US, Europe, South America)" | restricted, eu=T | anywhere ✗, eu=T ✓ | ✓ ✓ |
| Remote but "only" by hours | Search Atlas, "REMOTE (anywhere, EST hours)" | restricted, eu=T | anywhere ✗, eu ✓ | restricted ✓, eu=F ✗ |
| Job seeker, "Location:" format | 50344555 | not job | job ✗ | not job ✓ |
| "SEEKING" that is a company hiring | getregistered, "SEEKING FREELANCER / Remote - UK or EU" | job, eu=T | ✓ ✓ | not job ✗, eu=F ✗ |
| Non-post "." | 50382129 | not job | job ✗ | ✓ |
| AI only in the blurb | Starbridge (AI platform, React frontend role) | ai=F | ai=T ✗ | ✓ |
| AI role listed in the body of a multi-role post | Shepherd (1 MLE among SWEs) | ai=T | ✓ | ai=F ✗ |
| Funding, not salary | Shepherd "$42M Series B"; Sunsave "£113m Series A" | sal=F | sal=T ✗ | sal=T ✗ |
| Signing bonus, not salary | Odoo "€10k signing bonus" | sal=F | ✗ | ✗ |
| Placeholder pay | "[salary range]"; "$XXX/hour" | sal=F | ✓ | ✓ |
| Hourly / monthly / CHF | Search Atlas $23-34/hr; Collabify $3-4k/month; CERN CHF 9,236/month | sal=T | ✓ | ✓ |
| "Work remotely" but only for people at a Bay Area company | "New Product" moonlighting post | restricted, eu=F | anywhere ✗, eu=T ✗ | anywhere ✗, eu=T ✗ |

All per-post predictions are in `results/{naive,regex}_per_post.csv` (one row per post per run, with `*_ok` columns).

## Verdict

**Not established.** The arc can't be confirmed or refuted without the Jev and LLM runs. What the keyless numbers
already say:

1. **"Code Mode with keyword matching is cheap but wrong" depends on the script the model writes.** A naive script
   overcounts the headline by 35 of 46 (+76%) on the key, and by ~60 on the full month: that's the demo's story. A
   careful header regex is within 3 of 46 on the headline count, because its 11 wrong posts cancel. If the Code Mode
   agent in setup 2 writes the careful kind of script, the headline count won't look wrong on stage.
2. **Counts hide errors; per-post lists show them.** On "AI roles open to EU remote" the careful regex predicts 10
   against a key of 9, yet 11 posts are wrong. For the "wrong" beat to land, the demo should show or score the list
   of posts, not just the number.
3. **`ai_role` is where keywords fail hardest** (careful regex: precision 0.64, recall 0.57; naive: precision 0.35).
   It's the field most likely to separate Jev from regex, and the best candidate for the headline. The salary traps
   (funding, signing bonuses) fool both keyword scripts at precision ~0.78.
4. **The key's ambiguity caps any score.** 43 of 158 labels are judgement calls, mostly on `ai_role` and hours-based
   remote, and 9 of the careful regex's 11 EU errors sit on them. Settle those labels before reading Jev's accuracy
   as right or wrong.

## How to run the rest once keys exist

```bash
bash .sammy/setup.sh                                  # uv sync --frozen
cd spike
uv run python fetch_data.py                           # no-op: months are cached
uv run python eval_classifier.py regex --runs 3       # also: naive
```

Still to build, against the `Post` schema in `classifiers.py`: the Jev classifier (`Agent('typesafe:jev-latest',
output_type=Post)`, one call per post, confidence from `provider_details`), the LLM classifier, setups 1-4 with
Logfire, and the DynamicWorkflow/Temporal smoke test. Before running Jev, the question wording belongs on the `Post`
fields (docstrings, `BoolCriteria`).
