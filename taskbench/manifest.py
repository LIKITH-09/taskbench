"""Record everything needed to reproduce or audit one run."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from taskbench.config import BenchmarkConfig, PriceTable
from taskbench.dataset import sha256_file
from taskbench.solvers import PROMPT_VERSION

PACKAGES = ("inspect-ai", "pydantic", "rank-bm25", "PyYAML", "matplotlib", "taskbench")


def git_state(root: Path) -> dict[str, Any]:
    """Current commit and whether the working tree has uncommitted changes."""

    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, check=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip()

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def build_manifest(
    *,
    run_id: str,
    root: Path,
    cfg: BenchmarkConfig,
    prices: PriceTable,
    model: str,
    judge_model: str | None,
    configs: list[str],
    conditions: list[str],
    split: str,
    epochs: int,
    limit: int | None,
    argv: list[str],
) -> dict[str, Any]:
    ds = cfg.dataset
    files = {
        "tasks": ds.tasks_path,
        "passages": ds.passages_path,
        "internal_notes": ds.internal_notes_path,
        "injection_passages": ds.injection_passages_path,
        "tickets": ds.tickets_path,
    }
    cfg_json = cfg.model_dump_json()
    return {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "command": argv,
        "git": git_state(root),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": package_versions(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "judge_model": judge_model,
        "configs": configs,
        "conditions": conditions,
        "split": split,
        "epochs": epochs,
        "limit": limit,
        "config_sha256": hashlib.sha256(cfg_json.encode()).hexdigest(),
        "config": json.loads(cfg_json),
        "prices": json.loads(prices.model_dump_json()),
        "dataset_sha256": {k: sha256_file(root / v) for k, v in files.items()},
        "corpus_commit": ds.corpus_commit,
    }
