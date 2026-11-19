"""The job: Hacker News "Who is hiring?" posts and the five questions asked about each one."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

DATA = Path(__file__).parents[2] / "data"
THREAD = 50338728
"""Ask HN: Who is hiring? (November 2026). The 158 posts we labelled by hand are in it."""

Posts = dict[int, str]


class PostAnswers(BaseModel):
    """Read one top-level comment from an HN 'Ask HN: Who is hiring?' thread and label it."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    is_job: bool
    """Does the post offer paid or equity work? Job seekers, ads, empty posts and non-job programs are false.
    Expired posts, recruiter posts, commission-only and equity-only roles are true."""

    remote: Literal["anywhere", "restricted", "onsite_or_hybrid", "unclear"]
    """anywhere: remote with no region limit, or only a soft preference such as 'US/EU timezones preferred'.
    restricted: remote limited to countries or regions, or to required working hours.
    onsite_or_hybrid: no remote option; a location with no mention of remote counts here.
    unclear: no location given, or not a job. For several roles, take the most permissive option."""

    open_to_eu_remote: bool
    """Could someone living in an EU country take this job remotely? UK-only and US-only are false. Required
    hours an EU resident can meet (for example 4 hours overlap with US East) are true."""

    ai_role: bool
    """Is a listed role's title AI/ML, or is the role's main work building AI, ML, LLM or agent systems?
    AI in the company blurb, 'use AI tools', or one agent bullet among many does not count. True if any listed
    role qualifies."""

    salary_listed: bool
    """Does the post give a pay figure for the role (yearly, hourly, monthly, stipend, any currency)? Funding,
    revenue, market size, signing bonuses, 'competitive' and placeholders like '[salary range]' are false."""


class Labeled(PostAnswers):
    id: int
    """The post id given above the post."""


class Post(BaseModel):
    id: int
    text: str


QUESTIONS = "\n".join(f"- {name}: {field.description}" for name, field in PostAnswers.model_fields.items())
POSTS: Posts = {p.id: p.text for p in map(Post.model_validate_json, (DATA / "posts.jsonl").open())}
