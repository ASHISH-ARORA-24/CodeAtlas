ITERATION 9 — Multi-Agent 🚀

Only now split the responsibilities.

                  ORCHESTRATOR
                       │
        ┌──────────────┼─────────────┐
        ↓              ↓             ↓
    Planning         Coding        Testing
     Agent            Agent         Agent
                       │
                       ↓
                    Review
                     Agent

Example:

User
"Add low-stock warning"
       ↓
Orchestrator
       ↓
Planner
       ↓
Implementation Plan
       ↓
Coder
       ↓
Chroma + Neo4j
       ↓
Modify code
       ↓
Tester
       ↓
Tests fail
       ↓
Coder
       ↓
Fix
       ↓
Tester
       ↓
Pass
       ↓
Reviewer
       ↓
PR
Learn

Multi-agent systems
Orchestrator/Supervisor
Specialized agents
Agent-to-agent communication
Delegation
Shared state
Single-agent vs multi-agent trade-offs

This last point is especially important for architecture interviews:

Why 4 agents instead of 1 agent with 10 tools?

We should be able to defend either architecture.
