"""Step 4: step 3, but when Jev is unsure about a post, Sonnet reads it instead."""

from pydantic_ai import Agent, AgentRunResult, ModelResponse, Tool
from pydantic_ai.capabilities import ModelFallback
from pydantic_ai.durable_exec.temporal import TemporalDurability
from pydantic_ai.exceptions import ContentFilterError, ModelAPIError
from pydantic_ai_harness import CodeMode

from hiring import hn, step3_jev_reads
from hiring.plumbing.config import ACTIVITIES
from hiring.plumbing.scoring import Job, save_labels
from hiring.posts import Labeled, PostAnswers


# Jev gives each answer a confidence from 0 (coin flip) to 1 (certain).
def unsure(response: ModelResponse) -> bool:
    return min((response.provider_details or {}).get('confidence', {}).values(), default=1.0) < 0.5


# NEW: below 0.5 on any answer, or if Jev is down, Sonnet reads the post instead; GPT if Sonnet refuses it.
reader = Agent('typesafe:jev-latest', output_type=PostAnswers, capabilities=[
    ModelFallback('anthropic:claude-sonnet-5-5', 'openai:gpt-6-luna',
                  fallback_on=[ModelAPIError, ContentFilterError, unsure]),
])


async def read_post(post_id: int) -> Labeled | None:
    """Fetch one post from Hacker News and have a small model label it. None if the post was deleted."""
    if not (text := await hn.get_post(post_id)):
        return None
    answers = (await reader.run(text)).output
    return Labeled(id=post_id, **answers.model_dump())


# The rest is step 3.
TOOLS = [hn.get_thread, read_post, Tool(save_labels, metadata={'temporal': False})]
agent = Agent('anthropic:claude-sonnet-5-5', name='step4', tools=TOOLS, capabilities=[
    CodeMode(max_tool_calls=400),  # ~300 read_post calls; default 100
    ModelFallback('openai:gpt-6-luna'),  # If Sonnet refuses or is down, GPT answers.
    TemporalDurability(activity_config=ACTIVITIES),
])
agents = [agent]


async def label(job: Job) -> AgentRunResult[str]:
    prompt = step3_jev_reads.prompt(job)
    result = await agent.run(prompt, instructions=step3_jev_reads.INSTRUCTIONS)
    return result
