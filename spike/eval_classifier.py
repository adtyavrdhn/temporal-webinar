"""Score a per-post classifier against the frozen answer key, and count the headline question per month.

Headline question: "how many job posts were remote and open to someone in the EU?"
(is_job and open_to_eu_remote).

Usage: uv run python eval_classifier.py regex [--runs 3]
Writes results/<name>_per_post.csv, results/<name>_per_field.csv, results/<name>_monthly.csv.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import pandas as pd

from classifiers import FIELDS, naive_classify, regex_classify

HERE = Path(__file__).parent
DATA, RESULTS = HERE / 'data', HERE / 'results'
CLASSIFIERS = {'naive': naive_classify, 'regex': regex_classify}
KEY_SHA = '4a112c59c382df4523baf1867a8dc35a7d56f65df8a557b990c372285bc7b20b'


def load_key() -> pd.DataFrame:
    body = (DATA / 'answer_key.jsonl').read_bytes()
    assert hashlib.sha256(body).hexdigest() == KEY_SHA, 'answer key changed: it is frozen'
    return pd.read_json(DATA / 'answer_key.jsonl', lines=True)


def load_posts(month: str) -> pd.DataFrame:
    return pd.read_json(DATA / f'posts_{month}.jsonl', lines=True)


def headline(df: pd.DataFrame) -> pd.Series:
    return df['is_job'] & df['open_to_eu_remote']


def per_field(merged: pd.DataFrame) -> list[dict]:
    rows = []
    for field in FIELDS:
        truth, pred = merged[f'{field}_key'], merged[f'{field}_pred']
        row = {'field': field, 'n': len(merged), 'correct': int((truth == pred).sum()), 'accuracy': (truth == pred).mean()}
        if truth.dtype == bool:
            tp = int((truth & pred).sum())
            fp = int((~truth & pred).sum())
            fn = int((truth & ~pred).sum())
            row |= {'tp': tp, 'fp': fp, 'fn': fn,
                    'precision': tp / (tp + fp) if tp + fp else float('nan'),
                    'recall': tp / (tp + fn) if tp + fn else float('nan')}
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('classifier', choices=CLASSIFIERS)
    parser.add_argument('--runs', type=int, default=3)
    args = parser.parse_args()
    classify = CLASSIFIERS[args.classifier]
    RESULTS.mkdir(exist_ok=True)

    key = load_key()
    nov = load_posts('2026-11').set_index('id')
    per_post, field_rows, monthly_rows = [], [], []
    for run in range(1, args.runs + 1):
        t0 = time.perf_counter()
        preds = pd.DataFrame([{'id': i, **classify(nov.loc[i, 'text']).model_dump()} for i in key['id']])
        wall = time.perf_counter() - t0
        merged = key.merge(preds, on='id', suffixes=('_key', '_pred'))
        for field in FIELDS:
            merged[f'{field}_ok'] = merged[f'{field}_key'] == merged[f'{field}_pred']
        merged['run'] = run
        per_post.append(merged)
        for row in per_field(merged):
            field_rows.append({'classifier': args.classifier, 'run': run, 'wall_s': wall, **row})

        # Headline count on the answer-key sample, and extrapolated to the whole month with the strata weights.
        truth = merged['is_job_key'] & merged['open_to_eu_remote_key']
        pred = merged['is_job_pred'] & merged['open_to_eu_remote_pred']
        full = pd.DataFrame([classify(t).model_dump() for t in nov['text']])
        monthly_rows.append({
            'classifier': args.classifier, 'run': run, 'month': '2026-11',
            'sample_n': len(merged), 'sample_key': int(truth.sum()), 'sample_pred': int(pred.sum()),
            'sample_error': int(pred.sum() - truth.sum()),
            'full_n': len(nov), 'full_key_extrapolated': float((merged['weight'] * truth).sum()),
            'full_pred': int(headline(full).sum()),
            'full_pred_from_sample_weights': float((merged['weight'] * pred).sum()),
        })
        monthly_rows[-1]['full_error_vs_extrapolated'] = monthly_rows[-1]['full_pred'] - monthly_rows[-1]['full_key_extrapolated']

    # The other eleven months have no key: record the classifier's own series once.
    for month in json.loads((DATA / 'threads.json').read_text()):
        if month == '2026-11':
            continue
        posts = load_posts(month)
        full = pd.DataFrame([classify(t).model_dump() for t in posts['text']])
        monthly_rows.append({'classifier': args.classifier, 'run': 1, 'month': month, 'full_n': len(posts),
                             'full_pred': int(headline(full).sum())})

    pd.concat(per_post).to_csv(RESULTS / f'{args.classifier}_per_post.csv', index=False)
    fields = pd.DataFrame(field_rows)
    fields.to_csv(RESULTS / f'{args.classifier}_per_field.csv', index=False)
    monthly = pd.DataFrame(monthly_rows).sort_values(['month', 'run'])
    monthly.to_csv(RESULTS / f'{args.classifier}_monthly.csv', index=False)
    print(fields[fields.run == 1].drop(columns=['classifier', 'run', 'wall_s']).to_string(index=False))
    print(monthly.to_string(index=False))


if __name__ == '__main__':
    main()
