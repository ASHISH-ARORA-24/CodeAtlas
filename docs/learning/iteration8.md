ITERATION 8 — Observability / Tracing

Now instrument the agent.

For every request we should be able to see:

Task
 ↓
Agent decision
 ↓
search_code()       450 ms
 ↓
OpenAI              1.2 sec / 800 tokens
 ↓
get_dependencies()  120 ms
 ↓
OpenAI              1.1 sec / 600 tokens
 ↓
write_file()
 ↓
run_tests()          3.4 sec
 ↓
Final response

TOTAL:
8.7 seconds
3,200 tokens
$X cost
7 tool calls
Learn

Tracing
Logs
Metrics
LLM calls
Tool traces
Latency
Token monitoring
Failure analysis
