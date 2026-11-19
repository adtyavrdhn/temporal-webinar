"""Step 3: Sonnet writes a script that runs in the worker, and the script hands each post to Jev."""

from pydantic_ai import Agent, AgentRunResult, Tool
from pydantic_ai.capabilities import ModelFallback
from pydantic_ai.durable_exec.temporal import TemporalDurability
from pydantic_ai_harness import CodeMode

from hiring import hn
from hiring.plumbing.config import ACTIVITIES
from hiring.plumbing.scoring import Job, save_labels
from hiring.posts import Labeled, PostAnswers

# Jev, a small decision model, answers one post.

reader = Agent("typesafe:jev-latest", output_type=PostAnswers)


async def read_post(post_id: int) -> Labeled | None:
    """Fetch one post from Hacker News and have a small model label it. None if the post was deleted."""
    if not (text := await hn.get_post(post_id)):
        return None
    answers = (await reader.run(text)).output
    return Labeled(id=post_id, **answers.model_dump())


# Code Mode as in step 2, with the script run by Monty in the worker. Under Temporal each tool call is an activity.
TOOLS = [hn.get_thread, read_post, Tool(save_labels, metadata={"temporal": False})]
agent = Agent(
    "anthropic:claude-sonnet-5-5",
    name="step3",
    tools=TOOLS,
    capabilities=[
        CodeMode(max_tool_calls=400),  # ~300 read_post calls; default 100
        ModelFallback("openai:gpt-6-luna"),  # If Sonnet refuses or is down, GPT answers.
        TemporalDurability(activity_config=ACTIVITIES),
    ],
)
agents = [agent]

INSTRUCTIONS = "Work in code. Never print or read post text or labels yourself."


def prompt(job: Job) -> str:
    return (
        f"{job.task} Call read_post for every post, all at once, then pass the ones that are not None to "
        "save_labels in one call. Count in code, then reply with one sentence: how many job posts are remote "
        "and open to someone in the EU."
    )


async def label(job: Job) -> AgentRunResult[str]:
    result = await agent.run(prompt(job), instructions=INSTRUCTIONS)
    return result
