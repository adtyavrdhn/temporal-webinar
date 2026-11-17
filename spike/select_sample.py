"""Pick the answer-key sample from the Nov 2026 thread, stratified so every trap is present.

Each post goes into exactly one stratum (the first trap hint it matches, in the order below);
a fixed fraction of each stratum is drawn with a fixed seed. The weight N_stratum / n_stratum on
every sampled post lets the key extrapolate to full-month counts.
Writes data/sample_2026-11.jsonl (id, stratum, weight, text). Deterministic: same cache, same sample.
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / 'data'
SEED = 20261117
TARGET = 150

MONEY = r'[$€£]\s?\d|\d\s?(k|K)\b|\b(USD|EUR|GBP|CHF|CAD|SEK|PLN)\b'
STRATA = [
    # (name, predicate on (header, text)), first match wins
    ('no_pipe_header', lambda h, t: '|' not in h),
    ('seeking_or_location', lambda h, t: re.search(r'\bSEEKING\b|^Location:', t, re.M) is not None),
    ('remote_restricted', lambda h, t: re.search(r'remote', h, re.I) is not None
        and re.search(r'\b(US|USA|U\.S\.|Canada|EU|Europe|UK|EMEA|CET|EST|PST|only|timezone|time zone|North America|LATAM)\b', h, re.I) is not None),
    ('funding_money', lambda h, t: re.search(r'(raised|series [a-e]|seed|funding|revenue|ARR|valuation|backed)', t, re.I) is not None
        and re.search(MONEY, t) is not None),
    ('odd_pay', lambda h, t: re.search(r'/\s?(hr|hour|h|month|mo)\b|per (hour|month)|€|£|CHF|\bEUR\b|\bGBP\b', t, re.I) is not None),
    ('ai_header', lambda h, t: re.search(r'\b(AI|ML|LLM|machine learning|agents?)\b', h, re.I) is not None),
    ('ai_blurb_only', lambda h, t: re.search(r'\b(AI|ML|LLMs?|machine learning|agents?|agentic)\b', t, re.I) is not None),
    ('multi_role', lambda h, t: len(re.findall(r'engineer|developer|designer|manager|scientist|lead', h, re.I)) >= 2),
    ('other', lambda h, t: True),
]


def header(text: str) -> str:
    return text.split('\n', 1)[0]


def main() -> None:
    rows = [json.loads(line) for line in (DATA / 'posts_2026-11.jsonl').open()]
    by_stratum: dict[str, list[dict]] = {name: [] for name, _ in STRATA}
    for row in rows:
        name = next(n for n, pred in STRATA if pred(header(row['text']), row['text']))
        by_stratum[name].append(row)

    frac = TARGET / len(rows)
    rng = random.Random(SEED)
    sample = []
    for name, members in by_stratum.items():
        # Small trap strata are oversampled (taken whole); the rest at the common fraction.
        k = len(members) if len(members) <= 12 else max(1, round(len(members) * frac))
        picked = rng.sample(members, k)
        weight = len(members) / k
        sample += [{'id': r['id'], 'stratum': name, 'weight': weight, 'text': r['text']} for r in picked]
        print(f'{name:22} {len(members):4} -> {k:3} (weight {weight:.3f})')
    sample.sort(key=lambda r: r['id'])
    (DATA / 'sample_2026-11.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in sample))
    print('sample', len(sample), Counter(r['stratum'] for r in sample))


if __name__ == '__main__':
    main()
