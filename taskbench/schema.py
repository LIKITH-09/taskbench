"""Validated record types shared by the dataset, the runner and the report.

Every model forbids unknown fields, so a typo in a JSONL file fails loudly
instead of silently dropping data.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskKind = Literal["single_hop", "multi_hop", "unanswerable", "conflicting", "tool"]
SplitName = Literal["dev", "heldout"]
ConfigName = Literal["baseline", "rag", "agent", "agent_faults"]
Condition = Literal["main", "injection"]
PassageOrigin = Literal["docs", "internal_note", "injection"]
RunStatus = Literal["success", "error", "limit_reached"]
ToolName = Literal["search_docs", "lookup_ticket"]
TicketStatus = Literal["open", "in_progress", "blocked", "resolved"]

CONFIG_NAMES: tuple[str, ...] = get_args(ConfigName)
TASK_KINDS: tuple[str, ...] = get_args(TaskKind)

TASK_ID_PATTERN = r"^Q\d{4}$"
PASSAGE_ID_PATTERN = r"^(P|N|X)\d{4}$"
TICKET_ID_PATTERN = r"^TCK-\d{4}$"


class Strict(BaseModel):
    """Base model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


class Passage(Strict):
    """A citable chunk of the retrieval corpus."""

    id: str = Field(pattern=PASSAGE_ID_PATTERN)
    source_path: str = Field(min_length=1)
    source_commit: str | None = None
    heading: str
    text: str = Field(min_length=1)
    license: str
    origin: PassageOrigin = "docs"


class Ticket(Strict):
    """A fictional support ticket served by the ``lookup_ticket`` tool."""

    id: str = Field(pattern=TICKET_ID_PATTERN)
    title: str = Field(min_length=1)
    status: TicketStatus
    component: str = Field(min_length=1)
    priority: Literal["low", "medium", "high"]
    owner: str = Field(min_length=1)
    opened: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: str = ""


class BenchmarkTask(Strict):
    """One benchmark question with everything needed to score it."""

    id: str = Field(pattern=TASK_ID_PATTERN)
    split: SplitName
    kind: TaskKind
    question: str = Field(min_length=1)
    answer_keywords: list[str] = Field(default_factory=list)
    reference_answer: str = ""
    supporting_passages: list[str] = Field(default_factory=list)
    required_tools: list[ToolName] = Field(default_factory=list)
    ticket_ids: list[str] = Field(default_factory=list)
    stale_keywords: list[str] = Field(default_factory=list)
    prompt_injection: bool = False
    injection_marker: str | None = None
    review_status: Literal["draft", "reviewed"] = "draft"
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_consistency(self) -> BenchmarkTask:
        if self.kind == "unanswerable":
            if self.answer_keywords or self.supporting_passages:
                raise ValueError(f"{self.id}: unanswerable tasks take no keywords or passages")
        elif not self.answer_keywords:
            raise ValueError(f"{self.id}: answerable tasks need answer_keywords")
        if self.kind in ("single_hop", "multi_hop", "conflicting") and not self.supporting_passages:
            raise ValueError(f"{self.id}: {self.kind} tasks need supporting_passages")
        if self.kind == "tool" and "lookup_ticket" not in self.required_tools:
            raise ValueError(f"{self.id}: tool tasks must require lookup_ticket")
        if "lookup_ticket" in self.required_tools and not self.ticket_ids:
            raise ValueError(f"{self.id}: tasks requiring lookup_ticket must list ticket_ids")
        if self.kind == "conflicting" and not self.stale_keywords:
            raise ValueError(f"{self.id}: conflicting tasks need stale_keywords")
        if self.prompt_injection:
            if self.split != "heldout":
                raise ValueError(f"{self.id}: injection tasks must be held out")
            if not self.injection_marker:
                raise ValueError(f"{self.id}: injection tasks need an injection_marker")
        elif self.injection_marker:
            raise ValueError(f"{self.id}: injection_marker set on a non-injection task")
        return self


class ResultRow(Strict):
    """One attempted execution of one task, in one epoch, under one configuration.

    Metrics that do not apply (for example citation precision for the baseline)
    are ``None``, never zero.
    """

    run_id: str
    config: ConfigName
    condition: Condition = "main"
    model: str
    task_id: str = Field(pattern=TASK_ID_PATTERN)
    split: SplitName
    kind: TaskKind
    epoch: int = Field(ge=1)
    status: RunStatus
    error_type: str | None = None
    success: bool
    abstained: bool = False
    conflict_flagged: bool | None = None
    judged_success: bool | None = None
    cited_count: int | None = Field(default=None, ge=0)
    citation_precision: float | None = Field(default=None, ge=0, le=1)
    retrieval_recall: float | None = Field(default=None, ge=0, le=1)
    text_tool_call: bool | None = None
    tool_calls: int = Field(default=0, ge=0)
    tool_calls_invalid: int = Field(default=0, ge=0)
    tool_errors: int = Field(default=0, ge=0)
    required_tools_called: bool | None = None
    injected_faults: int = Field(default=0, ge=0)
    recovered: bool | None = None
    injection_exposed: bool = False
    injection_resisted: bool | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_s: float | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    answer: str = ""

    @model_validator(mode="after")
    def check_consistency(self) -> ResultRow:
        if self.status != "success" and self.success:
            raise ValueError("a failed execution cannot be a success")
        if self.injection_resisted is not None and not self.injection_exposed:
            raise ValueError("injection_resisted requires injection_exposed")
        if self.recovered is not None and self.injected_faults == 0:
            raise ValueError("recovered only applies when a fault was injected")
        if self.tool_calls_invalid > self.tool_calls or self.tool_errors > self.tool_calls:
            raise ValueError("tool error counts cannot exceed tool_calls")
        return self


class HumanLabel(Strict):
    """A blind human judgement of one result row, used for scorer calibration."""

    run_id: str
    config: ConfigName
    task_id: str = Field(pattern=TASK_ID_PATTERN)
    epoch: int = Field(ge=1)
    label: Literal["correct", "incorrect"]
    labeler: str = Field(min_length=1)
    notes: str = ""
