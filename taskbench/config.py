"""Load and validate ``configs/benchmark.yaml`` and ``configs/prices.yaml``.

The YAML file is the single source of truth for counts, seeds and run settings.
The CLI reads it and lets command-line flags override individual values.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from taskbench.schema import CONFIG_NAMES, TASK_KINDS, ConfigName


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetConfig(Section):
    tasks_path: str
    passages_path: str
    internal_notes_path: str
    injection_passages_path: str
    tickets_path: str
    tickets_db: str
    human_labels_path: str
    corpus_repo: str
    corpus_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    corpus_license: str
    passages_sha256: str | None = None
    split_seed: int
    dev_count: int = Field(ge=1)
    heldout_count: int = Field(ge=1)
    injection_task_count: int = Field(ge=0)
    kind_counts: dict[str, int]

    @model_validator(mode="after")
    def check_counts(self) -> DatasetConfig:
        if set(self.kind_counts) != set(TASK_KINDS):
            raise ValueError(f"kind_counts must cover exactly {TASK_KINDS}")
        if sum(self.kind_counts.values()) != self.dev_count + self.heldout_count:
            raise ValueError("kind_counts must sum to dev_count + heldout_count")
        return self


class RetrievalConfig(Section):
    k: int = Field(ge=1, le=50)


class GenerationConfig(Section):
    temperature: float = Field(ge=0)
    max_tokens: int = Field(ge=1)
    seed: int


class RunConfig(Section):
    model: str
    epochs: int = Field(ge=1)
    message_limit: int = Field(ge=2)
    time_limit_s: int = Field(ge=1)
    fault_probability: float = Field(ge=0, le=1)
    fault_seed: int
    max_connections: int = Field(ge=1)
    log_dir: str


class JudgeConfig(Section):
    model: str | None = None


class BenchmarkConfig(Section):
    dataset: DatasetConfig
    retrieval: RetrievalConfig
    generation: GenerationConfig
    run: RunConfig
    judge: JudgeConfig
    configs: list[ConfigName]
    prices_path: str

    @model_validator(mode="after")
    def check_configs(self) -> BenchmarkConfig:
        if sorted(self.configs) != sorted(CONFIG_NAMES):
            raise ValueError(f"configs must list exactly {CONFIG_NAMES}")
        return self


class ModelPrice(Section):
    input_usd_per_million: float | None = Field(default=None, ge=0)
    output_usd_per_million: float | None = Field(default=None, ge=0)
    source_url: str | None = None
    checked_on: str | None = None

    @model_validator(mode="after")
    def check_source(self) -> ModelPrice:
        priced = self.input_usd_per_million is not None or self.output_usd_per_million is not None
        if priced and (not self.source_url or not self.checked_on):
            raise ValueError("a price needs source_url and checked_on")
        return self


class PriceTable(Section):
    prices: dict[str, ModelPrice]
    estimate_local_with: str | None = None
    notes: dict[str, str] = Field(default_factory=dict)

    def price_for(self, model: str) -> ModelPrice | None:
        """The model's own API price, or None if it is not in the table."""
        return self.prices.get(model)

    def reference_price(self) -> ModelPrice | None:
        """The priced model named by ``estimate_local_with``, used for labelled estimates."""
        if not self.estimate_local_with:
            return None
        ref = self.prices.get(self.estimate_local_with)
        if ref is None or ref.input_usd_per_million is None:
            raise ValueError(f"estimate_local_with={self.estimate_local_with!r} has no price")
        return ref


def token_cost(price: ModelPrice | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
    """Cost in USD for the given usage; None if the price or the usage is unknown."""
    if price is None or input_tokens is None or output_tokens is None:
        return None
    if price.input_usd_per_million is None or price.output_usd_per_million is None:
        return None
    return (
        input_tokens * price.input_usd_per_million + output_tokens * price.output_usd_per_million
    ) / 1_000_000


def load_config(path: Path) -> BenchmarkConfig:
    """Read and validate the benchmark configuration."""
    with path.open(encoding="utf-8") as f:
        return BenchmarkConfig.model_validate(yaml.safe_load(f))


def load_prices(path: Path) -> PriceTable:
    """Read and validate the price table."""
    with path.open(encoding="utf-8") as f:
        return PriceTable.model_validate(yaml.safe_load(f))
