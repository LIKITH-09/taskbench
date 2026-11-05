"""Inspect tools for the agent configurations, with seeded fault injection.

Per-sample bookkeeping lives in the Inspect sample ``store`` (saved in the log),
so ``report.py`` can read exactly what each sample retrieved and which faults
were injected:

* ``retrieved_ids``: passage IDs returned by any search, in order
* ``injected_faults``: number of simulated tool timeouts
* ``injection_exposed``: True once an injection passage was shown to the model
* ``tool_call_index``: running count of tool invocations (drives fault decisions)
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai.tool import Tool, ToolError, tool
from inspect_ai.util import store

from taskbench.faults import fault_fires
from taskbench.make_tickets import get_ticket
from taskbench.retrieval import BM25Index, format_passages

FAULT_MESSAGE = "simulated timeout: the tool did not respond"


def record_retrieval(passage_ids: list[str]) -> None:
    """Append retrieved IDs to the sample store and flag injection exposure."""
    s = store()
    s.set("retrieved_ids", [*s.get("retrieved_ids", []), *passage_ids])
    if any(pid.startswith("X") for pid in passage_ids):
        s.set("injection_exposed", True)


def _maybe_fault(seed: int, probability: float) -> None:
    s = store()
    index = int(s.get("tool_call_index", 0))
    s.set("tool_call_index", index + 1)
    if fault_fires(seed, str(s.get("sample_key", "")), index, probability):
        s.set("injected_faults", int(s.get("injected_faults", 0)) + 1)
        raise TimeoutError(FAULT_MESSAGE)


@tool
def search_docs(index: BM25Index, k: int = 5, fault_probability: float = 0.0, fault_seed: int = 0) -> Tool:
    """Search the documentation corpus."""

    async def execute(query: str) -> str:
        """Search the Inspect AI documentation and internal notes.

        Args:
            query: Keywords describing what you are looking for.

        Returns:
            Matching passages, each labelled with its passage ID in brackets.
        """
        _maybe_fault(fault_seed, fault_probability)
        hits = index.search(query, k=k)
        if not hits:
            return "No matching passages."
        record_retrieval([h.passage.id for h in hits])
        return format_passages(hits)

    return execute


@tool
def lookup_ticket(db_path: str, fault_probability: float = 0.0, fault_seed: int = 0) -> Tool:
    """Look up a support ticket."""

    async def execute(ticket_id: str) -> str:
        """Look up a support ticket by its ID.

        Args:
            ticket_id: The ticket ID, for example TCK-1001.

        Returns:
            The ticket's fields as text.
        """
        _maybe_fault(fault_seed, fault_probability)
        ticket = get_ticket(Path(db_path), ticket_id)
        if ticket is None:
            raise ToolError(f"No ticket with ID {ticket_id!r} exists.")
        return "\n".join(f"{k}: {v}" for k, v in ticket.model_dump().items())

    return execute
