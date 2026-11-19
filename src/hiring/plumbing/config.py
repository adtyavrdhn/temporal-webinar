"""Models, Temporal connection and Logfire setup shared by every step."""

from datetime import timedelta

import logfire
from dotenv import load_dotenv
from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.workflow import ActivityConfig

load_dotenv()  # API keys from .env; see .env.example.

# For every activity: model calls, tool calls and sandbox turns. One Sonnet call can take ~110 s, so allow 5 minutes.
# 5 s heartbeats mean a stopped worker's calls move to another worker within seconds. Temporal retries forever by
# default; 3 tries means a broken call fails the run instead of hanging it, and lets ModelFallback move on.
ACTIVITIES = ActivityConfig(
    start_to_close_timeout=timedelta(minutes=5),
    heartbeat_timeout=timedelta(seconds=5),
    retry_policy=RetryPolicy(maximum_attempts=3),
)

TEMPORAL = 'localhost:7233'
TASK_QUEUE = 'hiring'


def setup_logfire(service: str) -> None:
    """Sends traces when a Logfire token is found (LOGFIRE_TOKEN or `logfire projects use`); otherwise a no-op."""
    logfire.configure(service_name=service, send_to_logfire='if-token-present', console=False)
    logfire.instrument_pydantic_ai()  # Agent runs, model calls and tool calls.
    logfire.instrument_monty()  # The scripts Code Mode writes, with their inputs, outputs and tool calls.


async def connect() -> Client:
    # PydanticAIPlugin: Pydantic serialization and each workflow's agent activities.
    # LogfirePlugin: replay-safe Temporal and agent traces. Temporal metrics off: traces are what we show.
    return await Client.connect(TEMPORAL, plugins=[PydanticAIPlugin(), LogfirePlugin(metrics=False)])
