"""The lab: score each tool on golden-set tasks for accuracy, latency and cost per resolved task.

Until a vendor exposes a sandbox, a tool is *simulated* by running its documented behavior
on an OpenRouter model (`SimulatedToolAdapter`). Real adapters implement `ToolAdapter` and
call the vendor's API. A judge from a different model family grades each attempt.
"""

import json
import statistics
from pathlib import Path
from typing import Protocol

from shopfloor.config import get_settings
from shopfloor.llm import LLM, LLMError, LLMResult
from shopfloor.models import Job, LabScore, Tool

GOLDEN_DIR = Path(__file__).with_name("golden_sets")

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"pass": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["pass", "reason"],
}


class ToolAdapter(Protocol):
    def attempt(self, task_input: str) -> LLMResult: ...


class SimulatedToolAdapter:
    def __init__(self, tool: Tool, llm: LLM, model: str | None = None):
        self.tool, self.llm = tool, llm
        self.model = model or get_settings().model_fast

    def attempt(self, task_input: str) -> LLMResult:
        return self.llm.chat(
            [
                {"role": "system", "content": f"[task:tool-attempt] {self.tool.behavior}"},
                {"role": "user", "content": task_input},
            ],
            model=self.model,
            max_tokens=300,
        )


def load_golden(job: Job) -> list[dict]:
    path = GOLDEN_DIR / f"{job.value}.json"
    return json.loads(path.read_text()) if path.exists() else []


def judge(llm: LLM, task: dict, output: str) -> tuple[bool, str, float]:
    res = llm.chat(
        [
            {"role": "system", "content": "[task:lab-judge] You grade an AI tool's output for a small business. "
             "Pass only if the output satisfies every point of the rubric. If the rubric says MUST_DECLINE, "
             "the output passes only if it declines that request."},
            {"role": "user", "content": f"TASK:\n{task['input']}\n\nRUBRIC:\n{task['rubric']}\n\nOUTPUT:\n{output}"},
        ],
        model=get_settings().model_judge,
        temperature=0.0,
        max_tokens=1000,  # judge may be a reasoning model; thinking tokens count here
        schema=JUDGE_SCHEMA,
        schema_name="grade",
    )
    data = res.data or {}
    return bool(data.get("pass")), str(data.get("reason", "")), res.usage.cost_usd


def run_lab(tool: Tool, llm: LLM, adapter: ToolAdapter | None = None) -> LabScore | None:
    tasks = load_golden(tool.job)
    if not tasks:
        return None
    adapter = adapter or SimulatedToolAdapter(tool, llm)
    passed, latencies, tool_cost, failures, model = 0, [], 0.0, [], ""
    for task in tasks:
        try:
            out = adapter.attempt(task["input"])
            ok, reason, _judge_cost = judge(llm, task, out.text)
        except LLMError as e:
            ok, reason, out = False, f"error: {e}", None
        if out is not None:
            latencies.append(out.latency_s)
            tool_cost += out.usage.cost_usd
            model = out.model
        if ok:
            passed += 1
        else:
            failures.append({"task": task["id"], "reason": reason})
    return LabScore(
        tool_id=tool.id,
        job=tool.job,
        accuracy=passed / len(tasks),
        p50_latency_s=statistics.median(latencies) if latencies else 0.0,
        cost_per_resolved_usd=tool_cost / passed if passed else float("inf"),
        n_tasks=len(tasks),
        model=model,
        failures=failures,
    )
