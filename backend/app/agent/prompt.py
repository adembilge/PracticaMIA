from app.agent.state import AgentState

_LANGUAGE_NAMES = {"en": "English", "it": "Italian"}

_SYSTEM_PROMPT = """You are PracticaMIA, an assistant for Italian public-administration procedures.
You answer only from the SOURCE CHUNKS below.
You explain published official procedures.
Write in {language_name}.
If the chunks do not contain the fact, say that the indexed official pages do not state it.
State a fee, deadline, form name, or office only when those words appear in a chunk.
When two chunks disagree, follow the chunk with the later fetched_at and mention that date.
Say that the local comune, questura, ASL, or INPS office can apply the national rule differently.
Do not write a URL.
After the answer, on its own line, write:
CITATIONS: id1,id2
Use only chunk ids from the chunks. If none apply, write:
CITATIONS:
If a different Italian search query would match the official pages better, add one line:
REFINE: short query in Italian
Otherwise omit REFINE."""


def _format_chunk(chunk: dict) -> str:
    return (
        f"id: {chunk['id']}\n"
        f"title: {chunk['title']}\n"
        f"fetched_at: {chunk['fetched_at']}\n"
        f"heading: {chunk['heading']}\n"
        f"content: {chunk['content']}"
    )


def _format_history(history: list[dict]) -> str:
    return "\n\n".join(f"{entry['role']}: {entry['content']}" for entry in history)


def _build_user_content(state: AgentState) -> str:
    parts: list[str] = ["HISTORY"]
    if state["history"]:
        parts.append(_format_history(state["history"]))
    parts.append("SOURCE CHUNKS")
    if state["chunks"]:
        parts.append("\n\n".join(_format_chunk(chunk) for chunk in state["chunks"]))
    parts.append(f"QUESTION\n{state['question']}")
    return "\n\n".join(parts)


def build_prompt(state: AgentState) -> list[dict]:
    language_name = _LANGUAGE_NAMES[state["language"]]
    system_content = _SYSTEM_PROMPT.format(language_name=language_name)
    user_content = _build_user_content(state)
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]