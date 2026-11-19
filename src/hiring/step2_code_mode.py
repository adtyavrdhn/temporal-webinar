"""Step 2: Sonnet writes a script that fetches and labels the posts, and it runs in a Logfire Agent Sandbox."""

import logfire
from pydantic_ai import Agent, AgentRunResult, Tool
from pydantic_ai.capabilities import ModelFallback
from pydantic_ai.durable_exec.temporal import TemporalDurability
from pydantic_ai_harness import CodeMode

from hiring import hn
from hiring.plumbing.config import ACTIVITIES
from hiring.plumbing.scoring import Job, save_labels
from hiring.posts import QUESTIONS

# get_thread and get_posts call Hacker News, so under Temporal they are activities. save_labels only writes to
# memory: no activity.
# A remote sandbox pauses and saves the script at every tool call, so the script gets one call that fetches them all.
TOOLS = [Tool(hn.get_thread), Tool(hn.get_posts), Tool(save_labels, metadata={'temporal': False})]

# CodeMode: Sonnet writes one Python script that calls the tools; the post text never enters its context.
# monty_sandbox: the script runs in a Logfire Agent Sandbox. Under Temporal each stretch of script between two tool
# calls is an activity, and the sandbox saves the script there, so any worker can pick it up.
agent = Agent('anthropic:claude-sonnet-5-5', name='step2', tools=TOOLS, capabilities=[
    CodeMode(monty_sandbox=logfire.agent_sandboxes),
    ModelFallback('openai:gpt-6-luna'),  # If Sonnet refuses or is down, GPT answers.
    TemporalDurability(activity_config=ACTIVITIES),
])
agents = [agent]

INSTRUCTIONS = 'Work in code. Label the posts with code only: never print or read post text yourself.'


async def label(job: Job) -> AgentRunResult[str]:
    prompt = (f'{job.task} Fetch them with get_posts, label each one, and call save_labels once with all '
              'of them. Then reply with one sentence: how many job posts are remote and open to someone in the EU.\n'
              + QUESTIONS)
    result = await agent.run(prompt, instructions=INSTRUCTIONS)
    return result
