# ruff: noqa: E501
"""HTML views for the research supervisor browser surfaces."""

from __future__ import annotations

from html import escape


def graph_html(mermaid_graph: str) -> str:
    """Return a standalone Mermaid graph page."""

    escaped_graph = escape(mermaid_graph)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Supervisor Graph</title>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "base" }});
  </script>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #1d2433;
      background: #f7f8fb;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ margin: 0 0 28px; color: #5d667a; line-height: 1.5; }}
    .graph-shell {{
      overflow: auto;
      border: 1px solid #d8dde8;
      border-radius: 8px;
      background: white;
      padding: 24px;
    }}
    .mermaid {{ min-width: 760px; }}
  </style>
</head>
<body>
  <main>
    <h1>Research Supervisor Graph</h1>
    <p>
      The supervisor delegates research tasks, executes tool calls, and loops
      until the gathered notes are ready for a later report writer.
    </p>
    <div class="graph-shell">
      <pre class="mermaid">{escaped_graph}</pre>
    </div>
  </main>
</body>
</html>
"""


def app_html() -> str:
    """Return the browser UI for running the research supervisor."""

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Supervisor</title>
  <style>
    :root {
      --ink: #1d2433;
      --muted: #626b7f;
      --line: #d9deea;
      --paper: #f6f7fb;
      --surface: #ffffff;
      --accent: #3267d6;
      --accent-strong: #214da6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
    }
    header, .composer {
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
    }
    header h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    header p { margin: 4px 0 0; color: var(--muted); line-height: 1.4; }
    main {
      width: min(980px, 100%);
      margin: 0 auto;
      padding: 24px;
    }
    textarea {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      font: inherit;
      line-height: 1.45;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    label { color: var(--muted); font-size: 14px; }
    input {
      width: 72px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      font: inherit;
    }
    button {
      border: 0;
      border-radius: 8px;
      min-height: 40px;
      padding: 10px 16px;
      color: white;
      background: var(--accent);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { background: var(--accent-strong); }
    button:disabled { cursor: wait; opacity: 0.65; }
    .status { color: var(--muted); min-height: 20px; margin-top: 10px; }
    .result {
      margin-top: 20px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 18px;
    }
    .result h2 { margin: 0 0 12px; font-size: 18px; }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      line-height: 1.5;
      font-family: inherit;
      margin: 0;
    }
  </style>
</head>
<body>
  <header>
    <h1>Research Supervisor</h1>
    <p>Delegate a research brief to one or more local Ollama-guided research sub-agents.</p>
  </header>
  <main>
    <section class="composer">
      <form id="supervisor-form">
        <textarea id="brief" autofocus>Compare recent approaches to AI coding assistants from OpenAI, Anthropic, and Google, focusing on agentic coding workflows.</textarea>
        <div class="controls">
          <label>Supervisor loops <input id="supervisorIterations" type="number" min="1" max="6" value="4"></label>
          <label>Parallel agents <input id="parallelAgents" type="number" min="1" max="3" value="3"></label>
          <label>Search loops <input id="searchIterations" type="number" min="1" max="4" value="1"></label>
          <label>Results/query <input id="results" type="number" min="1" max="5" value="2"></label>
          <button id="run" type="submit">Run supervisor</button>
        </div>
        <div class="status" id="status"></div>
      </form>
    </section>
    <section class="result" hidden>
      <h2>Delegated Research Notes</h2>
      <pre id="notes"></pre>
    </section>
    <section class="result" hidden>
      <h2>Raw Sub-Agent Notes</h2>
      <pre id="raw"></pre>
    </section>
  </main>
  <script>
    const form = document.querySelector("#supervisor-form");
    const brief = document.querySelector("#brief");
    const supervisorIterations = document.querySelector("#supervisorIterations");
    const parallelAgents = document.querySelector("#parallelAgents");
    const searchIterations = document.querySelector("#searchIterations");
    const results = document.querySelector("#results");
    const run = document.querySelector("#run");
    const status = document.querySelector("#status");
    const notesSection = document.querySelectorAll(".result")[0];
    const rawSection = document.querySelectorAll(".result")[1];
    const notes = document.querySelector("#notes");
    const raw = document.querySelector("#raw");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const value = brief.value.trim();
      if (!value) return;
      run.disabled = true;
      status.textContent = "Coordinating sub-agents...";
      notesSection.hidden = true;
      rawSection.hidden = true;
      try {
        const response = await fetch("/api/supervisor", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            research_brief: value,
            max_supervisor_iterations: Number(supervisorIterations.value),
            max_concurrent_researchers: Number(parallelAgents.value),
            max_search_iterations: Number(searchIterations.value),
            max_results_per_query: Number(results.value)
          })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Supervisor run failed");
        notes.textContent = (payload.notes || []).join("\\n\\n---\\n\\n");
        raw.textContent = (payload.raw_notes || []).join("\\n\\n---\\n\\n");
        notesSection.hidden = false;
        rawSection.hidden = false;
        status.textContent = "Supervisor run complete.";
      } catch (error) {
        status.textContent = error.message;
      } finally {
        run.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


__all__ = ["app_html", "graph_html"]
