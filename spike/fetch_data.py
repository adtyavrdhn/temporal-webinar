"""Fetch and cache the last 12 "Ask HN: Who is hiring?" threads from the HN Algolia API.

Writes data/threads.json and data/posts_YYYY-MM.jsonl (top-level comments only, plain text).
Re-running skips months already cached, so runs are reproducible from the cache.
"""

import html
import json
import re
from datetime import datetime
from pathlib import Path

import httpx

DATA = Path(__file__).parent / 'data'
API = 'https://hn.algolia.com/api/v1'
TITLE = re.compile(r'^Ask HN: Who is hiring\? \((\w+) (\d{4})\)$')
MONTHS = [f'{y}-{m:02d}' for y, m in [(2025, 12)] + [(2026, m) for m in range(1, 12)]]


def to_text(comment_html: str) -> str:
    """HN comment HTML to plain text: paragraphs become blank lines, tags dropped, entities unescaped."""
    text = re.sub(r'<p>', '\n\n', comment_html)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def threads(client: httpx.Client) -> dict[str, int]:
    hits = client.get(f'{API}/search_by_date', params={'tags': 'story,author_whoishiring', 'hitsPerPage': 40}).json()['hits']
    found = {}
    for hit in hits:
        if m := TITLE.match(hit['title']):
            month = datetime.strptime(f'{m[1]} {m[2]}', '%B %Y').strftime('%Y-%m')
            if month in MONTHS:
                found[month] = int(hit['objectID'])
    return dict(sorted(found.items()))


def posts(client: httpx.Client, story_id: int) -> list[dict]:
    hits = client.get(f'{API}/search', params={'tags': f'comment,story_{story_id}', 'hitsPerPage': 1000}).json()['hits']
    rows = [
        {
            'id': int(h['objectID']),
            'story_id': story_id,
            'author': h.get('author'),
            'created_at': h.get('created_at'),
            'text': to_text(h.get('comment_text') or ''),
        }
        for h in hits
        if h.get('parent_id') == story_id
    ]
    return sorted(rows, key=lambda r: r['id'])


def main() -> None:
    DATA.mkdir(exist_ok=True)
    with httpx.Client(timeout=60) as client:
        thread_ids = threads(client)
        missing = sorted(set(MONTHS) - set(thread_ids))
        assert not missing, f'threads not found for {missing}'
        assert thread_ids['2026-11'] == 50338728
        (DATA / 'threads.json').write_text(json.dumps(thread_ids, indent=2) + '\n')
        for month, story_id in thread_ids.items():
            path = DATA / f'posts_{month}.jsonl'
            if path.exists():
                print(month, 'cached')
                continue
            rows = posts(client, story_id)
            path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
            print(month, story_id, len(rows), 'top-level posts')


if __name__ == '__main__':
    main()
