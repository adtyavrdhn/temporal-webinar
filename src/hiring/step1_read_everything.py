"""Step 1: Sonnet fetches every post from Hacker News with a tool and reads it."""

from pydantic_ai import Agent, AgentRunResult, Tool
from pydantic_ai.capabilities import ModelFallback
from pydantic_ai.durable_exec.temporal import TemporalDurability

from hiring import hn
from hiring.plumbing.config import ACTIVITIES
from hiring.plumbing.scoring import Job, save_labels

# TemporalDurability: inside a Temporal workflow, every model call and every tool call becomes an activity, saved
# when it finishes. save_labels only writes to memory: no activity.
agent = Agent(
    'anthropic:claude-sonnet-5-5',
    name='step1',
    tools=[hn.get_thread, hn.get_post, Tool(save_labels, metadata={'temporal': False})],
    capabilities=[
        ModelFallback('openai:gpt-6-luna'),  # If Sonnet refuses or is down, GPT answers.
        TemporalDurability(activity_config=ACTIVITIES),
    ],
)
agents = [agent]


async def label(job: Job) -> AgentRunResult[str]:
    # Sonnet calls get_post for each post (in parallel), so every post's text comes back into its context.
    prompt = (f'{job.task} Fetch them with get_post, label them, and save them with save_labels. Then reply with '
              'one sentence: how many job posts are remote and open to someone in the EU.')
    result = await agent.run(prompt, model_settings={'max_tokens': 32000})
    return result
