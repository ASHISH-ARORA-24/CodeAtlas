ITERATION 6 — Guardrails + Human-in-the-Loop

Now intentionally restrict our powerful agent.

For example:

Agent CAN:

✓ read files
✓ search code
✓ query Neo4j
✓ create issue
✓ create feature branch
✓ modify approved repository
✓ run tests
✓ create PR

But:

Agent CANNOT:

✗ push directly to main
✗ access arbitrary directories
✗ expose secrets
✗ delete repository
✗ execute arbitrary commands
✗ merge without approval

Workflow:

Agent
 ↓
PR
 ↓
Review
 ↓
HUMAN APPROVAL
 ↓
Merge
Learn

Guardrails
Human-in-the-loop
Tool authorization
Least privilege
Prompt injection considerations
Safe agent design


four small parts:

6A — Tool authorization policy
A central function decides whether a tool/action is allowed.
6B — File/repository guardrails
Restrict paths, block .env, secrets, arbitrary directories, destructive actions.
6C — Human-in-the-loop
Certain actions return approval_required instead of executing.
6D — Prompt-injection defense concept
Treat repository text as untrusted data; code/comments cannot override system/tool policy.


                 LLM
                  ↓
             write_file
                  ↓
       ┌── Tool authorization ──┐
       │       6A               │
       └────────↓───────────────┘
              ALLOW
                  ↓
       ┌── Resource guardrail ──┐
       │       6B               │
       │                        │
       │ repo allowed?          │
       │ path safe?             │
       │ sensitive file?        │
       │ destructive action?    │
       └────────↓───────────────┘
              ALLOW
                  ↓
            Actual write