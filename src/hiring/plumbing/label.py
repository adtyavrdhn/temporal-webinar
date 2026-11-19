"""Start one step on Temporal and print its score: `uv run label 1|2|3|4 [--posts N]`"""

import argparse
import asyncio
import time
from pathlib import Path

from hiring import hn
from hiring.plumbing.config import TASK_QUEUE, connect, setup_logfire
from hiring.plumbing.scoring import KEY, Job, print_receipt
from hiring.plumbing.workflows import STEPS
from hiring.posts import THREAD


async def _run(step: str, posts: int) -> None:
    setup_logfire('label')
    ids = (await hn.get_thread(THREAD))[:posts]
    job = Job(thread_id=THREAD, posts=len(ids), checked=[i for i in ids if i in KEY])
    start = time.perf_counter()
    # Whichever worker is up picks the run up; watch it in the Temporal UI.
    handle = await (await connect()).start_workflow(
        STEPS[step].run, job, id=f'step{step}-{int(time.time())}', task_queue=TASK_QUEUE)
    print(f'step {step}, {job.posts} posts: http://localhost:8233/namespaces/default/workflows/{handle.id}')
    result = await handle.result()
    result.seconds = time.perf_counter() - start
    print_receipt(result)
    # The scripts Sonnet wrote, to open in the editor. Each run replaces the last run's.
    runs = Path('runs')
    runs.mkdir(exist_ok=True)
    for old in runs.glob(f'step{step}-script*.py'):
        old.unlink()
    for n, script in enumerate(result.scripts, 1):
        path = runs / f'step{step}-script{n}.py'
        path.write_text(script)
        print(f'script {n}: {path}')


def main() -> None:
    parser = argparse.ArgumentParser(prog='label', description='Label posts with one step, on Temporal.')
    parser.add_argument('step', choices=list(STEPS))
    parser.add_argument('--posts', type=int, default=50, help="label the thread's first N posts (default 50)")
    args = parser.parse_args()
    asyncio.run(_run(args.step, args.posts))
