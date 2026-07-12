# Scope Module Video Script

Target length: 4-5 minutes.

## 0:00-0:25 - Intro

Say:

"In this module I implemented the scoping phase of the deep research agent. The
goal of this phase is not to research yet. It receives the user's initial
request, decides whether a follow-up question is needed, and then turns the
conversation into a clear research brief for the later research module."

Show:

```bash
cd ~/Documents/GitHub/deep-research-with-langgraph
```

## 0:25-1:15 - Course Adherence

Say:

"This follows the LangChain course repo closely. The upstream notebook uses a
two-step LangGraph workflow: first `clarify_with_user`, then
`write_research_brief`. I kept that same graph shape, the structured-output
pattern, the date-aware prompts, and the conditional routing where the graph
either stops with a clarification question or continues to brief generation."

Show:

```bash
uv run python -m deep_research_langgraph.scope graph
```

Point out:

- `__start__ -> clarify_with_user`
- `clarify_with_user -> __end__` when clarification is needed
- `clarify_with_user -> write_research_brief -> __end__` when the request is clear

## 1:15-2:20 - Software Adaptation

Say:

"The creative adaptation is that I did not keep this as notebook-only code.
Since I want to build on it later, I implemented it as reusable Python software
under `src/deep_research_langgraph/scope`. The code is split by responsibility:
types and schemas, prompts, nodes, graph assembly, session handling, and the
CLI."

Show these files:

```text
src/deep_research_langgraph/scope/types.py
src/deep_research_langgraph/scope/nodes.py
src/deep_research_langgraph/scope/graph.py
src/deep_research_langgraph/scope/session.py
src/deep_research_langgraph/scope/cli.py
```

Say:

"Another adaptation is model usage. The course defaults to hosted models, but
this project uses the existing local Ollama factory. So the same structured
output idea runs locally with `langgraph-coder` and does not require paid LLM
API keys."

## 2:20-3:35 - Run The Module

Say:

"Now I will run the scope module with a clear request. Because the request
already names the comparison and evaluation dimensions, the graph should skip
asking a follow-up question and generate the brief."

Run:

```bash
uv run deep-research-scope run "Compare Gemini Deep Research and OpenAI Deep Research for a solo developer deciding which to use for technical research, focusing on source quality, cost, report usefulness, and exportability."
```

Point out:

- the assistant verification message
- the generated research brief
- the brief's explicit criteria and open considerations

Say:

"If the initial request is vague, this same command asks a follow-up question in
the terminal, stores the answer in the conversation, and then tries again."

Optional quick demo:

```bash
uv run deep-research-scope run "Compare these research tools"
```

## 3:35-4:30 - Graph Export And Verification

Say:

"The graph is also displayable outside notebooks. I can print Mermaid directly
or save it as a file for documentation."

Run:

```bash
uv run deep-research-scope graph --output docs/scope_graph.mmd
```

Then run:

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

Say:

"The tests use fake model objects, so the unit tests do not depend on Ollama.
The real CLI run verifies that the actual local model path works."

## 4:30-5:00 - Close

Say:

"So this module is complete as a real software component. It closely follows
the course's scoping graph, while adapting it for this local-first project:
Python modules instead of notebooks, a reusable session wrapper, a CLI, graph
rendering, and Ollama-only model execution. The next module can consume the
`research_brief` field produced here."

