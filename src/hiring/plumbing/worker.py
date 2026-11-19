"""Runs all three steps. Start two; stop one mid-run and the other carries on: `uv run worker`"""

import asyncio
import time
from typing import Any

from temporalio import activity
from temporalio.worker import ActivityInboundInterceptor, ExecuteActivityInput, Interceptor, Worker

from hiring.plumbing.config import TASK_QUEUE, connect, setup_logfire
from hiring.plumbing.workflows import STEPS


class _PrintActivities(Interceptor):
    """Print each activity this worker runs, so you can see which worker is busy (and which one to stop)."""

    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        class Printing(ActivityInboundInterceptor):
            async def execute_activity(self, input: ExecuteActivityInput) -> Any:
                info = activity.info()
                print(f'{time.strftime("%H:%M:%S")}  {info.workflow_id}  {info.activity_type}', flush=True)
                return await super().execute_activity(input)

        return Printing(next)


async def _run() -> None:
    setup_logfire('worker')
    print('worker running')
    await Worker(await connect(), task_queue=TASK_QUEUE, workflows=list(STEPS.values()),
                 interceptors=[_PrintActivities()]).run()


def main() -> None:
    asyncio.run(_run())
