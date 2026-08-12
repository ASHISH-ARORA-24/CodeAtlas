ITERATION 3 — Code-Changing Agent

Now allow the agent to actually work on code.

Add tools:

read_file()
write_file()
run_tests()

Workflow:

Task
 ↓
Plan
 ↓
Find relevant code
 ↓
Analyze dependencies
 ↓
Modify code
 ↓
Run tests
 ↓
PASS?
 /   \
NO   YES
↓      ↓
Analyze Finish
failure
↓
Modify
↓
Test again

This gives us a genuine:

REASON
  ↓
ACT
  ↓
OBSERVE
  ↓
REASON
  ↓
ACT
Learn

Agent Loop deeply
Tool results
Error handling
Iteration
Planning + execution


3A — write_file()
Learn how the agent safely changes one file.

3B — run_tests()
Agent can validate its change.

3C — coding workflow
Plan → modify → test → fix → retest