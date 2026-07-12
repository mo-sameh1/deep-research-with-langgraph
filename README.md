# Deep Research with LangGraph

Local-first course workspace for Deep Research with LangGraph.

This setup mirrors the local Ollama approach from the adjacent
`langgraph-essentials-python` repository, while deliberately avoiding paid LLM,
observability, and hosting requirements. Course modules and labs are not
implemented yet.

## Ready-to-use stack

- Python 3.12 managed with `uv`
- LangGraph and LangChain
- `langchain-ollama` using the local `langgraph-coder` model
- JupyterLab/IPython kernel for course notebooks
- Ruff, Pyright, and Pytest for quality checks
- Local setup verification that does not call paid services

## Start a course session

```bash
cd ~/Documents/GitHub/deep-research-with-langgraph
cp -n .env.example .env
uv sync
uv run python -m deep_research_langgraph.check_setup
uv run jupyter lab
```

## Use Ollama in course code

Where a lesson constructs an OpenAI chat model, use the shared local factory:

```python
from deep_research_langgraph.models import get_chat_model

llm = get_chat_model()
```

Or construct it directly:

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="langgraph-coder",
    base_url="http://127.0.0.1:11434",
    temperature=0.2,
    num_ctx=32768,
)
```

## Quality commands

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

## Scope module

Start the browser app for the scoping phase:

```bash
uv run deep-research-scope app
```

Run the terminal version:

```bash
uv run python -m deep_research_langgraph.scope run "Compare Gemini Deep Research and OpenAI Deep Research for a solo developer deciding which to use"
```

Stream displayed responses:

```bash
uv run deep-research-scope run --stream "Compare Gemini Deep Research and OpenAI Deep Research"
uv run deep-research-scope app --stream
```

Display the LangGraph graph in a browser window:

```bash
uv run deep-research-scope display
```

## Research agent module

Run research from a brief:

```bash
uv run deep-research-agent run "Research the official LangGraph docs and explain what persistence, interrupts, and checkpoints are used for."
```

Start the browser app:

```bash
uv run deep-research-agent app
```

Display the research graph:

```bash
uv run deep-research-agent display
```

See [docs/SCOPE_MODULE.md](docs/SCOPE_MODULE.md) for the module notes and graph
export commands.

See [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md) for Ollama setup and
troubleshooting.
