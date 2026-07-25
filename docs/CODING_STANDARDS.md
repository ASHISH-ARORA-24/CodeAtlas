# CodeAtlas — Coding Standards

CodeAtlas indexes any repository regardless of how the code is written. These standards are not a gate — they are a guide.

The quality of answers CodeAtlas gives depends directly on the quality of the code it reads. Think of it like a search engine — it indexes everything, but well-structured content produces far better results. The same applies here.

When a repo follows these standards, CodeAtlas can:
- Embed richer meaning (docstrings + code together produce better vectors)
- Trace relationships more accurately (absolute imports and type hints build better graph edges)
- Answer deeper questions (single-purpose functions are easier for AI to reason about)

Repos that do not follow these standards will still be indexed — but answers may be shallower or less accurate.

---

## 1. Docstrings — Every Class and Function

Every class and every function must have a docstring. The docstring should explain **what** it does and **why** it exists — not just restate the function name.

CodeAtlas uses docstrings as part of the embedding. A function with a good docstring produces a much richer vector than code alone.

```python
# Bad — no docstring
def calculate_total(price: float, tax: float) -> float:
    return price + (price * tax / 100)


# Good — docstring explains what and why
def calculate_total(price: float, tax: float) -> float:
    """
    Calculates the final price after applying tax.

    Tax is treated as a percentage of the base price (e.g. tax=10 means 10%).
    This is used at checkout to compute the amount charged to the customer.
    """
    return price + (price * tax / 100)
```

---

## 2. Type Hints — All Parameters and Return Types

Every function parameter and return value must have a type declared. Type hints make the code self-documenting and allow CodeAtlas to build accurate graph edges (e.g. "this function returns a list of strings, and this other function accepts a list of strings — they are likely connected").

```python
# Bad — no type hints
def get_files(repo_path):
    pass


# Good — types declared
def get_files(repo_path: str) -> list[str]:
    pass


# Good — complex types
def build_graph(files: list[str]) -> dict[str, list[str]]:
    pass
```

---

## 3. Absolute Imports Only

Always import using the full path from the project root. Never use relative imports (dots).

Relative imports hide where something comes from. Absolute imports let CodeAtlas trace exactly which module depends on which, building accurate graph edges.

```python
# Bad — relative import, unclear where this comes from
from ..parser import parse_file
from .utils import clean_text

# Good — absolute import, path is explicit and traceable
from src.ingestion.parser import parse_file
from src.ingestion.utils import clean_text
```

---

## 4. Line Length — Maximum 120 Characters

No line of code should exceed 120 characters. Long lines are hard to read and review. Break long expressions across multiple lines.

```python
# Bad — too long
result = some_function(very_long_argument_one, very_long_argument_two, very_long_argument_three, very_long_argument_four)

# Good — broken across lines
result = some_function(
    very_long_argument_one,
    very_long_argument_two,
    very_long_argument_three,
    very_long_argument_four,
)
```

---

## 5. One Function, One Purpose

Every function must do exactly one thing. If you find yourself writing "and" when describing what a function does, split it into two functions.

Single-purpose functions produce cleaner graph nodes and are easier for CodeAtlas to reason about when answering structural questions.

```python
# Bad — this function does two things
def validate_and_save_user(user_data: dict) -> bool:
    """Validates user data and saves it to the database."""
    pass


# Good — two functions, one purpose each
def validate_user(user_data: dict) -> bool:
    """Checks that all required user fields are present and correctly formatted."""
    pass


def save_user(user_data: dict) -> bool:
    """Persists a validated user record to the database."""
    pass
```

---

## 6. No Magic Numbers — Use Named Constants

Never use unexplained numbers or strings directly in code. Assign them to a named constant at the top of the file. This makes the code readable and makes CodeAtlas answers more accurate ("MAX_CHUNK_SIZE is set to 500 tokens").

```python
# Bad — what does 500 mean?
if len(chunks) > 500:
    raise ValueError("Too many chunks")


# Good — the name explains the meaning
MAX_CHUNKS_PER_FILE = 500

if len(chunks) > MAX_CHUNKS_PER_FILE:
    raise ValueError(f"Chunk count exceeds limit of {MAX_CHUNKS_PER_FILE}")
```

---

## 7. README in Every Folder

Every folder (module, service, package) must contain a `README.md` that explains:
- What this folder contains
- Why it exists
- How it fits into the larger system

This gives CodeAtlas rich context when answering questions about project structure, and helps developers navigate unfamiliar codebases quickly.

---

## Summary Table

| Standard | Why It Matters for CodeAtlas |
|---|---|
| Docstrings | Richer embeddings — meaning + code combined |
| Type hints | Accurate graph edges between functions |
| Absolute imports | Traceable dependency graph |
| 120 char line limit | Readable, reviewable code |
| One function, one purpose | Clean graph nodes, easier AI reasoning |
| Named constants | Self-documenting, better AI answers |
| README in every folder | Structural context for Q&A |
