"""Prompt templates for the scope phase of the deep research workflow."""

CLARIFY_WITH_USER_INSTRUCTIONS = """
These are the messages that have been exchanged so far from the user asking for the report:
<Messages>
{messages}
</Messages>

Today's date is {date}.

Assess whether you need to ask a clarifying question, or if the user has already
provided enough information to write a useful research brief.
Do not start researching yet. This phase only decides the scope and prepares
the brief for later research.

IMPORTANT: If you can see in the messages history that you have already asked a
clarifying question, you almost always do not need to ask another one. Only ask
another question if absolutely necessary.

If there are acronyms, abbreviations, unknown terms, unclear entities, missing
comparison targets, or missing success criteria that would materially change
the report, ask the user to clarify.
If you need to ask a question, follow these guidelines:
- Be concise while gathering all necessary information.
- Gather the information needed to carry out the research task in a clear, well-structured manner.
- Use bullet points or numbered lists if appropriate.
- Do not ask for information the user has already provided.
- Prefer one focused follow-up question over a long interview.

Respond in valid JSON format with these exact keys:
"need_clarification": boolean,
"question": "<question to ask the user to clarify the report scope>",
"verification": "<verification message that we have enough information to write the research brief>"

If you need to ask a clarifying question, return:
"need_clarification": true,
"question": "<your clarifying question>",
"verification": ""

If you do not need to ask a clarifying question, return:
"need_clarification": false,
"question": "",
"verification": "<brief acknowledgement that enough information exists>"

For the verification message when no clarification is needed:
- Acknowledge that you have sufficient information to proceed.
- Briefly summarize the key aspects of the request.
- Confirm that you will prepare the research brief.
- Keep the message concise and professional.
"""

WRITE_RESEARCH_BRIEF_INSTRUCTIONS = """
You will be given a set of messages exchanged between the user and the scoping assistant.
Your job is to translate the conversation into a detailed, concrete research
brief that will guide a later research agent.

The messages exchanged so far are:
<Messages>
{messages}
</Messages>

Today's date is {date}.

Return a single research brief from the user's perspective.

Guidelines:
1. Maximize specificity and detail
- Include all known user preferences, constraints, success criteria, and
  requested output requirements.
- Preserve important details from the conversation, including clarification answers.

2. Handle unstated dimensions carefully
- When comprehensive research requires considering dimensions the user has not
  specified, label them as open considerations rather than assumed preferences.
- Example: instead of assuming "budget-friendly options," say "consider all
  price ranges unless cost constraints are specified."

3. Avoid unwarranted assumptions
- Never invent specific user preferences, constraints, entities, geography, dates, or requirements.
- If the user did not specify an important aspect, explicitly note that it is
  unspecified and should remain flexible.

4. Distinguish research scope from user preferences
- Research scope: topics, evidence, dimensions, and comparisons the researcher should investigate.
- User preferences: constraints or priorities the user actually stated.

5. Make the later report target clear
- State what the final research report should help the user decide, understand, compare, or produce.
- Name the kinds of evidence, sources, or evaluation criteria the researcher should look for.

6. Source guidance
- If specific sources should be prioritized, mention them.
- For product and travel research, prefer official or primary websites plus credible review sources.
- For academic or scientific queries, prefer original papers, official
  publications, or primary datasets.
- For people or organizations, prefer official websites, profiles, publications,
  and reputable reporting.
- If the query is in a specific language or region, prioritize sources matching that context.
"""
