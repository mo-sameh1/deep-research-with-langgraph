# Scope Module

The scope module turns an initial research request into a reusable research brief.
It follows the first module from
`langchain-ai/deep_research_from_scratch`: first decide whether clarification is
needed, then generate a detailed brief from the conversation.

This repository implements the module as reusable Python code instead of a
notebook.

## Run the scoping workflow

Start the browser app:

```bash
uv run deep-research-scope app
```

Run the terminal flow:

```bash
uv run python -m deep_research_langgraph.scope run "Compare Gemini Deep Research and OpenAI Deep Research for a solo developer deciding which to use"
```

If the model needs clarification, answer the follow-up question in the terminal.
When the request is scoped, the command prints the generated research brief.

## Display the graph

Open a Mermaid-rendered graph in a browser window:

```bash
uv run deep-research-scope display
```

Print Mermaid to the terminal:

```bash
uv run python -m deep_research_langgraph.scope graph
```

Write Mermaid to a file:

```bash
uv run python -m deep_research_langgraph.scope graph --output docs/scope_graph.mmd
```

Write a PNG image:

```bash
uv run python -m deep_research_langgraph.scope graph --output docs/scope_graph.png
```

## Design notes

- Close adherence: the graph keeps the course's two-node flow,
  structured-output schemas, date-aware prompts, and conditional routing.
- Local adaptation: the model is `ChatOllama` from the shared local model
  factory, not OpenAI.
- Software adaptation: code is split into `types`, `prompts`, `nodes`, `graph`,
  `session`, and `cli` modules so later research and report phases can reuse it.
