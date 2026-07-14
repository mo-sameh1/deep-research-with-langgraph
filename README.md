# Deep Research with LangGraph

Local-first course workspace for Deep Research with LangGraph.

This setup mirrors the local Ollama approach from the adjacent
`langgraph-essentials-python` repository, while keeping cloud integrations
explicitly opt-in. Ollama remains the default LLM backend; LangSmith is
supported for free-plan tracing and local LangGraph Studio demos. The final
module can optionally use Groq for a faster recorded run, but the project stays
local by default.

## Ready-to-use stack

- Python 3.12 managed with `uv`
- LangGraph and LangChain
- `langchain-ollama` using the local `langgraph-coder` model
- Optional `langchain-groq` for speeding up the final full-agent demo only
- JupyterLab/IPython kernel for course notebooks
- Ruff, Pyright, and Pytest for quality checks
- Optional LangSmith tracing and LangGraph Studio through the local CLI

## Start a course session

```bash
cd ~/Documents/GitHub/deep-research-with-langgraph
cp -n .env.example .env
uv sync
uv run python -m deep_research_langgraph.check_setup
uv run jupyter lab
```

## Optional LangSmith and Studio setup

LangSmith tracing is disabled by default. To record traces for a demo, create a
LangSmith API key, update `.env`, and keep the project name scoped to this repo:

```bash
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=lsv2-...
LANGSMITH_PROJECT=deep-research-with-langgraph
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=

TAVILY_API_KEY=tvly-...
TAVILY_SEARCH_DEPTH=basic
TAVILY_INCLUDE_ANSWER=false
TAVILY_INCLUDE_RAW_CONTENT=false
```

Then verify the setup:

```bash
uv run python -m deep_research_langgraph.langsmith.verify
```

Run either module with tracing enabled for that process:

```bash
uv run deep-research-scope run --trace "Compare local-first research agent architectures"
uv run deep-research-agent run --trace --max-search-iterations 1 --max-results-per-query 2 "Research LangGraph persistence, interrupts, and checkpoints."
```

Start local LangGraph Studio:

```bash
uv run langgraph dev --allow-blocking
```

Studio reads `langgraph.json` and exposes these graphs:

- `scope_research`
- `research_agent`
- `research_agent_mcp`
- `research_agent_supervisor`
- `deep_research_agent`

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

The research agent uses Tavily, matching the original course setup. Configure:

```bash
TAVILY_API_KEY=tvly-...
TAVILY_SEARCH_DEPTH=basic
```

Then run:

```bash
uv run deep-research-agent run --trace --max-search-iterations 1 --max-results-per-query 2 "Research the official LangGraph docs and explain what persistence, interrupts, and checkpoints are used for."
```

Start the browser app:

```bash
uv run deep-research-agent app
```

Display the research graph:

```bash
uv run deep-research-agent display
```

## MCP research agent module

The MCP module follows the course filesystem-server example. It uses local
Ollama for model calls and `npx -y @modelcontextprotocol/server-filesystem` to
expose the bundled `coffee_shops_sf.md` file as MCP tools.

List the available MCP tools:

```bash
uv run deep-research-mcp tools --sample-dir
```

Run MCP local-file research:

```bash
uv run deep-research-mcp run --trace --max-tool-iterations 4 "Which San Francisco coffee shops are associated with third-wave coffee or specialty roasting?"
```

Start the browser app:

```bash
uv run deep-research-mcp app --trace
```

Display the MCP graph:

```bash
uv run deep-research-mcp display
```

The first MCP command may download the filesystem server package through `npx`.

## Research supervisor module

The supervisor module follows the course multi-agent supervisor pattern. Local
Ollama acts as the lead researcher, Tavily-backed research sub-agents gather
evidence, and the supervisor aggregates compressed notes for a later report
writer.

Run supervised research:

```bash
uv run deep-research-supervisor run --trace --max-supervisor-iterations 4 --max-concurrent-researchers 3 --max-search-iterations 1 --max-results-per-query 2 "Compare recent approaches to AI coding assistants from OpenAI, Anthropic, and Google, focusing on agentic coding workflows."
```

The alias below runs the same module:

```bash
uv run deep-research-hypervisor run "Compare recent approaches to AI coding assistants from OpenAI, Anthropic, and Google."
```

Start the browser app:

```bash
uv run deep-research-supervisor app --trace
```

Display the supervisor graph:

```bash
uv run deep-research-supervisor display
```

## Full deep research agent module

The final module follows the course full-agent workflow: scoping,
multi-agent supervised research, and final report generation. All LLM calls use
local Ollama by default, while Tavily is used for the web-search research
sub-agents.

Run the full workflow with demo-sized budgets:

```bash
OLLAMA_WRITER_NUM_PREDICT=256 uv run deep-research-full run --trace --max-supervisor-iterations 2 --max-concurrent-researchers 1 --max-search-iterations 1 --max-results-per-query 1 "Research what LangGraph Studio is used for in local agent development and write a concise report with sources."
```

For a faster final-module recording, keep the same graph and switch only this
full-agent path to Groq:

```bash
export GROQ_API_KEY=gsk_...
uv run deep-research-full run --model-provider groq --trace --max-supervisor-iterations 2 --max-concurrent-researchers 1 --max-search-iterations 1 --max-results-per-query 1 "Research what LangGraph Studio is used for in local agent development and write a concise report with sources."
```

You can also put these in `.env` while recording:

```bash
FULL_AGENT_MODEL_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
GROQ_MAX_TOKENS=2048
```

Set `FULL_AGENT_MODEL_PROVIDER=ollama` or remove it to return to the fully local
default.

Start the browser app:

```bash
uv run deep-research-full app --trace
```

For Groq:

```bash
uv run deep-research-full app --model-provider groq --trace
```

Display the full graph:

```bash
uv run deep-research-full display
```
