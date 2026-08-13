ITERATION 7 — Evaluation

Now ask:

How do we know our agent is actually good?

Create perhaps 10–20 known tasks.

Example:

TASK:
"Add validation for negative stock."

EXPECTED:
Correct files identified
Correct dependencies identified
Correct change
Tests pass
No unrelated changes

Measure:

Task success
Tool selection accuracy
Retrieval quality
Correct files selected
Code correctness
Tests passed
Unnecessary tool calls
Hallucinations
Latency
Token consumption
Cost
Learn

Agent evaluation
LLM evaluation
Tool-call evaluation
Groundedness
Task completion
Regression testing


Agent Run
   ↓
Execution Trace
   ↓
┌─────────────────────┐
│ Deterministic checks│
└─────────────────────┘
   +
┌─────────────────────┐
│ LLM Judge           │
└─────────────────────┘
   ↓
Evaluation Result

For CodeAtlas, I would build Iteration 7 in four parts:

7A — Evaluation dataset
Create 5 known tasks first, not 20. Each task has expected files, expected behavior, and test expectations.
7B — Execution capture
Make code_agent.py return structured metadata like tools called, files read/written, test results, latency.
7C — Deterministic evaluator
Score things like task success, correct files, tests passed, unrelated changes, unnecessary tool calls.
7D — LLM judge
Evaluate groundedness, hallucination, reasoning quality, and final-answer correctness.