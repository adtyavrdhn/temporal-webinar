"""One Temporal workflow per step. Each is the step's `label()` with its agents listed for the worker."""

from temporalio import workflow

# Workflow code is sandboxed and re-imported by Temporal; these modules are safe to share as-is.
with workflow.unsafe.imports_passed_through():
    from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow

    from hiring import step1_read_everything, step2_code_mode, step3_jev_reads, step4_jev_then_sonnet
    from hiring.plumbing.scoring import Job, Tally, tally


@workflow.defn
class Step1(PydanticAIWorkflow):
    __pydantic_ai_agents__ = step1_read_everything.agents  # PydanticAIPlugin registers these agents' activities.

    @workflow.run
    async def run(self, job: Job) -> Tally:
        return await tally(job, step1_read_everything.label)


@workflow.defn
class Step2(PydanticAIWorkflow):
    __pydantic_ai_agents__ = step2_code_mode.agents

    @workflow.run
    async def run(self, job: Job) -> Tally:
        return await tally(job, step2_code_mode.label)


@workflow.defn
class Step3(PydanticAIWorkflow):
    __pydantic_ai_agents__ = step3_jev_reads.agents

    @workflow.run
    async def run(self, job: Job) -> Tally:
        return await tally(job, step3_jev_reads.label)


@workflow.defn
class Step4(PydanticAIWorkflow):
    __pydantic_ai_agents__ = step4_jev_then_sonnet.agents

    @workflow.run
    async def run(self, job: Job) -> Tally:
        return await tally(job, step4_jev_then_sonnet.label)


STEPS = {'1': Step1, '2': Step2, '3': Step3, '4': Step4}
