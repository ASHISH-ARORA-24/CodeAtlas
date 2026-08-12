# CodeAtlas Iteration 1 — Convert Fixed RAG Flow into First Agent

I have an existing CodeAtlas project.

Current flow:

```text
Project
  ↓
Python AST
  ↓
JSON
  ↓
Chunks → ChromaDB
Relations → Neo4j
  ↓
qa/ask.py
  ↓
Always search ChromaDB
  ↓
Always fetch Neo4j context
  ↓
Send combined context to Gemini
  ↓
Answer
```

Current command:

```bash
PYTHONPATH=. uv run python3 qa/ask.py codeatlas/ecommerce "what does StockManager.reserve_stock do?"
```

Important: the first argument is now **project scope**, not repo scope.

A project can contain one or more repositories.

Example:

```text
Project: codeatlas/ecommerce
├── repo1
├── repo2
└── repo3
```

## Goal

Create the first simple AI agent.

Do NOT implement multi-agent, LangGraph, MCP, memory, planning, GitHub automation, guardrails, or evaluation yet.

This iteration is only for learning:

* Agent
* Agent loop
* Tools
* OpenAI function/tool calling
* LLM deciding which tool to use

## Required Architecture

Change from this fixed flow:

```text
Question
   ↓
ChromaDB always
   ↓
Neo4j always
   ↓
LLM
```

to:

```text
Question
   ↓
OpenAI Agent
   ↓
Agent decides what information it needs
   ↓
Available tools:

search_code()
get_dependencies()
read_file()

   ↓
Execute requested tool
   ↓
Return tool result to OpenAI
   ↓
Agent decides whether another tool is needed
   ↓
Repeat until final answer
```

## Important Requirement

Do NOT rewrite the existing ChromaDB or Neo4j implementation.

Reuse the existing working logic from the project and wrap that logic as tools.

Keep `qa/ask.py` unchanged initially so it remains our old fixed-RAG baseline for comparison.

Create a new agent implementation separately.

Suggested structure:

```text
CodeAtlas/
├── agents/
│   └── code_agent.py
│
├── tools/
│   ├── code_search.py
│   ├── graph_tool.py
│   └── file_tool.py
│
└── qa/
    └── ask.py
```

You may adapt the structure if the existing repository architecture suggests something better, but keep the responsibilities separated.

## Tool 1 — search_code

Create a project-scoped tool conceptually like:

```python
search_code(project: str, query: str)
```

It should reuse the existing ChromaDB search logic.

It must search across all repositories belonging to the provided project.

Return enough metadata for the agent to understand where the result came from, ideally including:

```text
project
repo
file
symbol type
symbol name
code/chunk
similarity score
```

Tool description for the LLM should clearly explain:

> Use this tool to find relevant code, functions, methods, classes, or implementation based on semantic meaning.

## Tool 2 — get_dependencies

Create:

```python
get_dependencies(project: str, symbol: str)
```

Reuse the existing Neo4j graph/context logic.

This tool should answer relationship questions such as:

* what this function calls
* what calls this function
* class/method relationships
* file relationships
* dependency/impact relationships available in the current graph

It must be project-scoped.

Tool description:

> Use this tool when you need callers, callees, dependencies, relationships, or impact information for a code symbol.

## Tool 3 — read_file

Create something conceptually like:

```python
read_file(project: str, repo: str, path: str)
```

It should safely read an exact source file inside the selected project/repository.

Do not allow arbitrary filesystem access outside the CodeAtlas project repositories.

Tool description:

> Use this tool when exact source code needs to be inspected.

## OpenAI

Replace Gemini only for the new agent implementation.

Use the OpenAI API.

Use the modern OpenAI Python SDK/tool-calling approach already compatible with the project's dependencies.

The OpenAI API key must come from environment configuration. Do not hardcode credentials.

## Agent Loop

Implement a simple explicit loop so I can understand how agents work.

Conceptually:

```python
messages = [...]

while True:
    response = call_openai(messages, tools)

    if response contains tool calls:
        for tool_call in response.tool_calls:
            result = execute_requested_tool(tool_call)
            append_tool_result_to_conversation(result)
    else:
        return final_answer
```

Do not hide the agent loop behind a framework.

I want plain Python first so the mechanics are obvious.

## Logging / Console Output

Make the execution visible for learning.

For example:

```text
Question:
what does StockManager.reserve_stock do?

Agent decision:
Calling search_code

Tool arguments:
project=codeatlas/ecommerce
query=StockManager.reserve_stock

Tool result:
...

Agent decision:
Calling read_file

Tool arguments:
repo=...
path=stock_manager.py

Tool result:
...

Agent decision:
Enough information available

Final Answer:
...
```

The exact wording can differ, but I want to clearly see:

1. which tool the model selected
2. tool arguments
3. tool result
4. whether the model requested another tool
5. final answer

## New Command

Provide a command similar to:

```bash
PYTHONPATH=. uv run python3 agents/code_agent.py codeatlas/ecommerce "what does StockManager.reserve_stock do?"
```

## Tests / Success Criteria

Test at least these three questions.

### Test 1

```text
Where is stock reservation implemented?
```

Expected behavior:

Primarily use `search_code()`.

### Test 2

```text
What calls reserve_stock?
```

Expected behavior:

Primarily use `get_dependencies()`.

### Test 3

```text
Explain StockManager.reserve_stock and tell me what could be impacted if I change it.
```

Expected behavior:

The agent should be capable of combining tools, for example:

```text
search_code
read_file
get_dependencies
```

Do not hard-code the sequence for these questions.

The LLM must choose the tools.

## Important Constraints

* Do not modify AST ingestion unless necessary.
* Do not redesign ChromaDB.
* Do not redesign Neo4j.
* Do not introduce LangChain.
* Do not introduce LangGraph.
* Do not introduce MCP.
* Do not introduce multi-agent.
* Do not introduce memory/state persistence.
* Do not add GitHub SDLC automation yet.
* Keep this iteration small and easy to understand.
* Prefer reusing existing CodeAtlas modules rather than copying logic.
* Preserve existing `qa/ask.py` behavior for comparison.

## After Implementation

Explain to me:

1. What files were created or changed.
2. Where the agent loop is implemented.
3. Where OpenAI tool schemas are defined.
4. How a tool name returned by OpenAI maps to the Python function.
5. How tool results are sent back to OpenAI.
6. How project scope is preserved across all repository searches.
7. Any assumptions or limitations.

Do not proceed to Iteration 2.
