"""Fetch Inspect AI's documentation at a pinned commit and rebuild data/passages.jsonl.

The commit is read from configs/benchmark.yaml (dataset.corpus_commit), so the
corpus cannot silently drift. Requires git on PATH.

Usage:
    python scripts/fetch_corpus.py              # fetch, build passages, verify hash
    python scripts/fetch_corpus.py --keep DIR   # keep the checkout in DIR
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taskbench.config import load_config  # noqa: E402
from taskbench.corpus import build_passages, write_jsonl  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def checkout(repo_url: str, commit: str, dest: Path) -> None:
    """Shallow-fetch exactly one commit into ``dest``."""
    dest.mkdir(parents=True, exist_ok=True)
    run("git", "init", "-q", cwd=dest)
    run("git", "remote", "add", "origin", repo_url, cwd=dest)
    run("git", "fetch", "-q", "--depth", "1", "origin", commit, cwd=dest)
    run("git", "checkout", "-q", "FETCH_HEAD", cwd=dest)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", type=Path, default=None, help="Directory to keep the checkout in.")
    args = parser.parse_args(argv)

    cfg = load_config(ROOT / "configs" / "benchmark.yaml")
    ds = cfg.dataset
    out = ROOT / ds.passages_path
    with tempfile.TemporaryDirectory() as tmp:
        dest = args.keep or Path(tmp) / "inspect_ai"
        checkout(ds.corpus_repo, ds.corpus_commit, dest)
        passages = build_passages(dest / "docs", ds.corpus_commit, license_name=ds.corpus_license)
        n = write_jsonl(passages, out)

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"Wrote {n} passages to {out} (sha256 {digest[:16]}...)")
    if ds.passages_sha256 and digest != ds.passages_sha256:
        raise SystemExit(
            "passages.jsonl hash differs from configs/benchmark.yaml. The corpus or splitter "
            "changed; task supporting_passages may now point at the wrong text."
        )


if __name__ == "__main__":
    main()
