"""Collects each step's answers and scores them against the posts we labelled."""

from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel
from pydantic_ai import AgentRunResult, ModelResponse, ToolCallPart

from hiring.posts import DATA, Labeled, PostAnswers


class KeyRow(PostAnswers):
    id: int


KEY: dict[int, PostAnswers] = {
    row.id: PostAnswers.model_validate(row.model_dump(exclude={'id'}))
    for row in map(KeyRow.model_validate_json, (DATA / 'answer_key.jsonl').open())
}



class Job(BaseModel):
    """Label the first `posts` posts of a Hacker News thread, oldest first."""

    thread_id: int
    posts: int
    checked: list[int]
    """The posts among them that we labelled: the score counts these."""

    @property
    def task(self) -> str:
        return f'Hacker News thread {self.thread_id}: label its first {self.posts} posts (get_thread lists them).'


Label = Callable[[Job], Awaitable[AgentRunResult[str]]]
"""A step: do the job and return the agent's run."""

_answers: ContextVar[dict[int, PostAnswers]] = ContextVar('answers')


def save(post_id: int, answers: PostAnswers) -> None:
    """Record one post's answers for scoring."""
    _answers.get()[post_id] = PostAnswers.model_validate(answers.model_dump(include=set(PostAnswers.model_fields)))


@contextmanager
def _collecting() -> Generator[dict[int, PostAnswers]]:
    answers: dict[int, PostAnswers] = {}
    token = _answers.set(answers)
    try:
        yield answers
    finally:
        _answers.reset(token)


class Tally(BaseModel):
    ids: list[int]
    answer: str = ''
    labels: dict[int, PostAnswers] = {}
    cost: float = 0.0
    calls: int = 0
    seconds: float = 0.0
    scripts: list[str] = []
    """The scripts Sonnet wrote with Code Mode, in order."""

    @property
    def right(self) -> int:
        return sum(self.labels.get(i) == KEY[i] for i in self.ids)


async def save_labels(labels: list[Labeled]) -> str:
    """Save one entry per post: its id and the five answers."""
    for row in labels:
        save(row.id, row)
    return f'saved {len(labels)}'


async def tally(job: Job, label: Label) -> Tally:
    result = Tally(ids=job.checked)
    with _collecting() as labels:
        run = await label(job)
    result.answer, result.labels = run.output, labels
    result.cost, result.calls = float(run.usage.cost or 0), run.usage.requests
    result.scripts = [part.args_as_dict()['code'] for m in run.all_messages() if isinstance(m, ModelResponse)
                      for part in m.parts if isinstance(part, ToolCallPart) and part.tool_name == 'run_code']
    return result


def print_receipt(t: Tally) -> None:
    eu_jobs = sum(KEY[i].is_job and KEY[i].open_to_eu_remote for i in t.ids)
    print(f'\n{t.answer}\n')
    print(f'time   {t.seconds:.1f} s')
    print(f'cost   ${t.cost:.3f}  ({t.calls} model calls)')
    print(f'right  {t.right}/{len(t.ids)} posts')
    print(f'key    {eu_jobs} job posts are remote and open to the EU')
