"""HTML views for the scope workflow browser surfaces."""

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
  <title>Deep Research Scope Graph</title>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "base" }});
  </script>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1d2433;
      --muted: #5d667a;
      --line: #d8dde8;
      --paper: #f7f8fb;
    }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0 0 28px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .graph-shell {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 24px;
    }}
    .mermaid {{
      min-width: 680px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Scope Graph</h1>
    <p>
      The graph follows the course scoping flow: clarify the user request,
      then write the research brief.
    </p>
    <div class="graph-shell">
      <pre class="mermaid">{escaped_graph}</pre>
    </div>
  </main>
</body>
</html>
"""


def app_html() -> str:
    """Return the browser UI for the scope workflow."""

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deep Research Scope</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1d2433;
      --muted: #626b7f;
      --line: #d9deea;
      --paper: #f6f7fb;
      --surface: #ffffff;
      --user: #e7f0ff;
      --assistant: #f2f3f6;
      --brief: #ecf8f0;
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
    .layout {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: 100vh;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--surface);
      padding: 18px 24px;
    }
    header h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    header p {
      margin: 4px 0 0;
      color: var(--muted);
      line-height: 1.4;
    }
    #messages {
      width: min(920px, 100%);
      margin: 0 auto;
      padding: 24px;
    }
    .message {
      display: grid;
      gap: 6px;
      margin: 0 0 16px;
      max-width: 780px;
    }
    .message.user {
      margin-left: auto;
    }
    .label {
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }
    .bubble {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      line-height: 1.55;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: var(--assistant);
    }
    .user .bubble {
      background: var(--user);
      border-color: #bdd1f3;
    }
    .brief .bubble {
      background: var(--brief);
      border-color: #bfe3c8;
    }
    .composer {
      border-top: 1px solid var(--line);
      background: var(--surface);
      padding: 16px 24px;
    }
    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      width: min(920px, 100%);
      margin: 0 auto;
      align-items: end;
    }
    textarea {
      width: 100%;
      min-height: 72px;
      max-height: 180px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      font: inherit;
      line-height: 1.4;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 12px 18px;
      min-height: 46px;
      color: white;
      background: var(--accent);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover {
      background: var(--accent-strong);
    }
    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }
    .status {
      width: min(920px, 100%);
      margin: 8px auto 0;
      color: var(--muted);
      font-size: 13px;
      min-height: 18px;
    }
    @media (max-width: 680px) {
      form { grid-template-columns: 1fr; }
      button { width: 100%; }
      header, #messages, .composer {
        padding-left: 16px;
        padding-right: 16px;
      }
    }
  </style>
</head>
<body>
  <div class="layout">
    <header>
      <h1>Deep Research Scope</h1>
      <p>Ask for a research report. The app will clarify the scope or generate the brief.</p>
    </header>
    <main id="messages" aria-live="polite"></main>
    <section class="composer">
      <form id="scope-form">
        <textarea
          id="message"
          placeholder="Example: Compare Gemini and OpenAI Deep Research..."
          autofocus
        ></textarea>
        <button id="send" type="submit">Send</button>
      </form>
      <div class="status" id="status"></div>
    </section>
  </div>
  <script>
    const messages = document.querySelector("#messages");
    const form = document.querySelector("#scope-form");
    const textarea = document.querySelector("#message");
    const send = document.querySelector("#send");
    const status = document.querySelector("#status");

    function addMessage(role, content, extraClass = "") {
      const wrapper = document.createElement("article");
      wrapper.className = `message ${role} ${extraClass}`.trim();

      const label = document.createElement("div");
      label.className = "label";
      label.textContent = role === "user"
        ? "You"
        : extraClass === "brief"
          ? "Research brief"
          : "Scoping agent";

      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = content;

      wrapper.append(label, bubble);
      messages.append(wrapper);
      wrapper.scrollIntoView({ behavior: "smooth", block: "end" });
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const value = textarea.value.trim();
      if (!value) return;

      addMessage("user", value);
      textarea.value = "";
      send.disabled = true;
      status.textContent = "Thinking locally with Ollama...";

      try {
        const response = await fetch("/api/message", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: value })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Request failed");
        if (payload.assistant_message) addMessage("assistant", payload.assistant_message);
        if (payload.research_brief) addMessage("assistant", payload.research_brief, "brief");
        status.textContent = payload.research_brief ? "Scope complete." : "Clarification needed.";
      } catch (error) {
        status.textContent = error.message;
      } finally {
        send.disabled = false;
        textarea.focus();
      }
    });
  </script>
</body>
</html>
"""
