# CodeAtlas

CodeAtlas is an AI-powered codebase Q&A service. Give it a GitHub repository URL and ask questions about the code in plain English — it answers using the actual code as context.

## The Problem It Solves

When a developer joins a new team or revisits old code, they spend enormous time just figuring out *where things are* and *how they connect*. CodeAtlas lets you ask:

- "Where is the payment logic handled?"
- "What functions call the user authentication module?"
- "What will break if I change this function?"

And get answers grounded in the actual codebase.

## How It Works

1. You provide a public GitHub repository URL
2. CodeAtlas downloads the repository into a structured local folder
3. It converts the code into **embeddings** (vector representations of meaning) and stores them in a vector database
4. It also builds a **knowledge graph** capturing structural relationships (function calls, imports, class inheritance)
5. When you ask a question, it searches both the vectors and the graph to find relevant code
6. It sends that code + your question to an AI model and returns a grounded answer

## Local Repository Structure

Repos are stored locally under `source/` using this hierarchy:

```
source/
└── <owner>/
    └── <project>/
        └── <repo>/
```

Example — a microservices platform owned by `microsoft`:

```
source/
└── microsoft/
    └── ecommerce-platform/
        ├── payment-service/
        ├── inventory-service/
        └── user-service/
```

- **owner** — the GitHub user or organisation that owns the repos
- **project** — the logical system or product (one project can contain multiple repos/services)
- **repo** — a single repository, which could be one microservice within a larger project

This structure also drives the Neo4j knowledge graph hierarchy:
`(Owner) → (Project) → (Repo) → (File) → (Function/Class)`

This makes cross-repo questions possible — e.g. "what does the payment service call in the inventory service?"

## Tech Stack (Local / Free Phase)

| Purpose | Tool |
|---|---|
| Vector database | ChromaDB |
| Graph database | Neo4j (Community Edition) |
| Embeddings | Sentence Transformers (local, free) |
| AI Q&A | Gemini Flash (free tier) |

## Build Iterations

This project is built in three iterations of increasing complexity:

### Iteration 1 — Simple Scripts
Two or three Python scripts. No framework, no structure. Just get the end-to-end flow working: download repo → embed → ask question → get answer. Focus: understand the concepts.

### Iteration 2 — Structured Python Project
Proper project layout, modules, CLI or simple API. Introduce separation of concerns, config management, error handling. Focus: write code that is organized and maintainable.

### Iteration 3 — Microservices on Azure
Each concern (ingestion, embedding, graph, querying, API gateway) becomes its own service. Message queues, inter-service APIs, CI/CD pipelines, infrastructure as code. Focus: production-grade architecture.

## Learning Goal

This project exists to build deep, interview-ready knowledge of AI engineering — not just to ship a product. Every decision is explained. Every concept is understood before it is coded.
