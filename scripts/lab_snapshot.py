"""Run the scenario lab for every catalog tool with documented behavior and save the results with the repo.

The deployed demo then shows lab results without spending API credits per visitor.
These are SIMULATIONS of each vendor's documented behavior on an OpenRouter model, graded by a different model family.
Run: uv run python scripts/lab_snapshot.py   (needs OPENROUTER_API_KEY)
"""

import json

from shopfloor.catalog import catalog_tools
from shopfloor.lab.runner import run_lab
from shopfloor.llm import get_llm
from shopfloor.service import LAB_SNAPSHOT

llm = get_llm()
print("LLM:", type(llm).__name__)
results = []
for tool in catalog_tools():
    if not tool.behavior:
        continue
    score = run_lab(tool, llm)
    if score:
        results.append(score.model_dump(mode="json"))
        print(f"{tool.name:32} {score.accuracy:.0%} of {score.n_tasks}  model={score.model}  failures={[f['task'] for f in score.failures]}")
LAB_SNAPSHOT.write_text(json.dumps(results, indent=1), encoding="utf-8")
print("wrote", LAB_SNAPSHOT)
