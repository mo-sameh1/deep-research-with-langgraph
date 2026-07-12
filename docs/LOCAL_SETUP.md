# Local Setup

## Ollama baseline

This repository expects Ollama to listen on `127.0.0.1:11434` and to provide
the local `langgraph-coder` model.

Everyday commands:

```bash
systemctl --user status ollama
ollama list
ollama ps
ollama run langgraph-coder
journalctl --user -u ollama -f
```

Verify the project setup:

```bash
uv run python -m deep_research_langgraph.check_setup
```

The check confirms:

- `.env`-backed settings can be loaded
- Ollama is reachable locally
- the configured model is available
- cloud tracing and paid-provider keys are not required

## Model creation

The adjacent course repository already has `langgraph-coder` installed. If the
model ever needs to be rebuilt:

```bash
ollama create langgraph-coder -f ops/ollama/Modelfile
```

## Staying local-only

Keep these values in `.env` unless a later task explicitly opts into a service:

```dotenv
LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

This project does not require OpenAI, Anthropic, LangSmith uploads, hosted
databases, or app hosting for the setup stage.

