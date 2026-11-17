"""Per-post labels: the schema every classifier answers, and the keyword (regex) baseline.

The regex baseline is what a Code Mode script without a classifier model ends up doing: look at the
pipe header, match keywords, count. It is deterministic.
"""

import re
from typing import Literal

from pydantic import BaseModel

FIELDS = ['is_job', 'remote', 'open_to_eu_remote', 'ai_role', 'salary_listed']
Remote = Literal['anywhere', 'restricted', 'onsite_or_hybrid', 'unclear']


class Post(BaseModel):
    """Labels for one top-level post in an HN 'Who is hiring?' thread."""

    is_job: bool
    remote: Remote
    open_to_eu_remote: bool
    ai_role: bool
    salary_listed: bool


REGION = re.compile(
    r'\b(US|USA|U\.S\.?|United States|Canada|CA|North America|NA|Americas|LATAM|South America|EU|EEA|Europe|EMEA|UK|'
    r'CET|EST|ET|PST|PT|CST|timezones?|time zones?|hours|only|India|Brazil|Germany|Poland)\b',
    re.I,
)
EU = re.compile(r'\b(EU|EEA|Europe|European|EMEA|CET|Germany|France|Spain|Poland|Netherlands|Portugal|Ireland)\b', re.I)
AI = re.compile(r'\b(AI|ML|LLMs?|machine learning|deep learning|computer vision|GenAI|agentic|agents?|RL)\b', re.I)
MONEY = re.compile(r'([$€£¥]\s?\d)|(\d\s?[kK]\b)|(\b(USD|EUR|GBP|CHF)\s?\d)|(\d\s?(USD|EUR|GBP|CHF)\b)')


def header(text: str) -> str:
    return text.strip().split('\n', 1)[0]


def naive_classify(text: str) -> Post:
    """The first script a model tends to write: every post is a job, keywords anywhere count."""
    head = header(text)
    remote = 'anywhere' if re.search(r'remote', head, re.I) else 'onsite_or_hybrid'
    return Post(
        is_job=True,
        remote=remote,
        open_to_eu_remote=remote == 'anywhere',
        ai_role=AI.search(text) is not None,
        salary_listed=MONEY.search(text) is not None,
    )


def regex_classify(text: str) -> Post:
    """A careful keyword script: header-based, region words, AI only in the header, money anywhere."""
    head = header(text)
    is_job = '|' in head and not re.match(r'\s*(SEEKING|Location:)', head, re.I)
    if m := re.search(r'remote', head, re.I):
        after = head[m.start():m.start() + 60]
        remote = 'restricted' if REGION.search(after) else 'anywhere'
    elif re.search(r'onsite|on-site|hybrid|in[- ]office', head, re.I) or is_job:
        remote = 'onsite_or_hybrid'
    else:
        remote = 'unclear'
    eu = remote == 'anywhere' or (remote == 'restricted' and EU.search(head) is not None)
    return Post(
        is_job=is_job,
        remote=remote,
        open_to_eu_remote=is_job and eu,
        ai_role=is_job and AI.search(head) is not None,
        salary_listed=is_job and MONEY.search(text) is not None,
    )
