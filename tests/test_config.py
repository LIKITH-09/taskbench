from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from taskbench.config import BenchmarkConfig, ModelPrice, PriceTable, load_config, load_prices, token_cost
from taskbench.schema import CONFIG_NAMES
from tests.conftest import REPO_ROOT


def raw() -> dict:
    return yaml.safe_load((REPO_ROOT / "configs" / "benchmark.yaml").read_text(encoding="utf-8"))


def test_repo_config_loads():
    cfg = load_config(REPO_ROOT / "configs" / "benchmark.yaml")
    assert sorted(cfg.configs) == sorted(CONFIG_NAMES)
    assert cfg.dataset.dev_count + cfg.dataset.heldout_count == sum(cfg.dataset.kind_counts.values())


def test_config_list_must_match_schema():
    data = raw()
    data["configs"] = ["baseline", "rag"]
    with pytest.raises(ValidationError, match="configs"):
        BenchmarkConfig.model_validate(data)


def test_kind_counts_must_sum_to_split_counts():
    data = raw()
    data["dataset"]["kind_counts"]["tool"] += 1
    with pytest.raises(ValidationError, match="sum"):
        BenchmarkConfig.model_validate(data)


def test_unknown_config_key_rejected():
    data = raw()
    data["run"]["epoch"] = 3
    with pytest.raises(ValidationError):
        BenchmarkConfig.model_validate(data)


def test_commit_must_be_full_hash():
    data = raw()
    data["dataset"]["corpus_commit"] = "main"
    with pytest.raises(ValidationError):
        BenchmarkConfig.model_validate(data)


def test_repo_prices_load():
    prices = load_prices(REPO_ROOT / "configs" / "prices.yaml")
    assert prices.price_for("ollama/llama3.2") is not None
    ref = prices.reference_price()
    assert ref is not None and ref.source_url and ref.checked_on
    assert prices.price_for("ollama/qwen2.5:7b").input_usd_per_million == 0.0


def test_price_requires_source_and_date():
    with pytest.raises(ValidationError, match="source_url"):
        ModelPrice(input_usd_per_million=1.0, output_usd_per_million=2.0)


def test_reference_price_must_exist(tmp_path: Path):
    table = PriceTable(prices={}, estimate_local_with="openai/missing")
    with pytest.raises(ValueError, match="no price"):
        table.reference_price()


def test_token_cost():
    price = ModelPrice(
        input_usd_per_million=1.0,
        output_usd_per_million=4.0,
        source_url="https://example.com",
        checked_on="2026-10-22",
    )
    assert token_cost(price, 1_000_000, 500_000) == pytest.approx(3.0)
    assert token_cost(price, None, 10) is None
    assert token_cost(None, 10, 10) is None
