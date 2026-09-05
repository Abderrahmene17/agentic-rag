"""
agent.py — the piece that was missing: turns tools.py into something an
LLM can actually call, in a chat loop you can type into.

Key design choice: apply_type_update is NOT given to the model as a tool
at all. The model can only ever call propose_type_update (read-only draft).
When a proposal is pending, the NEXT user message is checked directly by
this script — if it's a yes, WE call apply_type_update ourselves, not the
model. This makes the confirmation structural, not something the model
could accidentally skip.

Install:
    pip install groq python-dotenv
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

import build_tools as tools  

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"  # swap for any Groq-hosted model

SYSTEM_PROMPT = (
    "You are an assistant for a company documents database. Use the tools "
    "to search, read, and (when needed) propose reclassifying a document's "
    "type. You cannot apply an update yourself — after calling "
    "propose_type_update, tell the user what you're proposing and that "
    "you're waiting for their yes/no."
)

# --- Tool schemas the model is allowed to see and call -----------------
# Notice apply_type_update is absent on purpose (see docstring above).
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_document",
            "description": "Fetch one document by its id, full content included.",
            "parameters": {
                "type": "object",
                "properties": {"doc_id": {"type": "integer"}},
                "required": ["doc_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Semantic search over document content. Returns matched excerpt + type + id per hit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "doc_type": {"type": "string", "description": "Optional filter."},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_document_types",
            "description": "Return every distinct document type in the database.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_type_update",
            "description": "Draft a reclassification WITHOUT writing to the DB. Always call this before suggesting a type change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "integer"},
                    "new_type": {"type": "string"},
                },
                "required": ["doc_id", "new_type"],
            },
        },
    },
]

# Maps tool name -> real Python function. apply_type_update is deliberately
# left out here too — even if the model somehow emitted a call for it,
# there'd be nothing to run.
TOOL_FUNCTIONS = {
    "get_document": tools.get_document,
    "search_documents": tools.search_documents,
    "list_document_types": tools.list_document_types,
    "propose_type_update": tools.propose_type_update,
}


MAX_HISTORY_TURNS = 5  # how many past user<->agent exchanges to keep in memory


def build_messages(history_turns, current_turn):
    """history_turns is a list of turns (each turn = a list of messages).
    Flatten the kept turns + the in-progress turn into one message list,
    with the system prompt always first."""
    flat_history = [m for turn in history_turns for m in turn]
    return [{"role": "system", "content": SYSTEM_PROMPT}] + flat_history + current_turn


def run_agent():
    history_turns = []  # completed turns only, oldest first
    pending_proposal = None  # {"doc_id": ..., "new_type": ...} while awaiting yes/no
 
    print("Agent ready. Type 'quit' to exit.\n")
 
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
 
        # A confirmation is handled directly by US, never routed through the model.
        if pending_proposal:
            if user_input.lower() in ("yes", "y", "confirm", "confirmed"):
                result = tools.apply_type_update(**pending_proposal)
                print(f"Agent: Done — {result}\n")
            else:
                print("Agent: Okay, cancelled that update.\n")
            pending_proposal = None
            continue
 
        current_turn = [{"role": "user", "content": user_input}]
 
        # Inner loop: let the model chain multiple tool calls before answering.
        while True:
            messages = build_messages(history_turns, current_turn)
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            current_turn.append(msg)
 
            if not msg.tool_calls:
                print(f"Agent: {msg.content}\n")
                break
 
            for call in msg.tool_calls:
                fn_name = call.function.name
                fn_args = json.loads(call.function.arguments)
 
                print(f"  [tool call] {fn_name}({fn_args})")
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
                print(f"  [tool result] {result}\n")
 
                if fn_name == "propose_type_update" and "error" not in result:
                    pending_proposal = {
                        "doc_id": result["doc_id"],
                        "new_type": result["proposed_type"],
                    }
 
                current_turn.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": fn_name,
                        "content": json.dumps(result),
                    }
                )
            # loop again so the model can respond to the tool result(s)
 
        # Turn is done — fold it into history, then keep only the last N turns.
        history_turns.append(current_turn)
        history_turns = history_turns[-MAX_HISTORY_TURNS:]
 
 
if __name__ == "__main__":
    run_agent()