# service/app/domain/metrics.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .models import ModelPackage
from .schemas import Scores
from ..integrations.github import reviewedness_score


# ---------------- Reproducibility ----------------
def run_reproducibility_check(pkg: ModelPackage, timeout: int = 10) -> float:
    """
    Try to reproduce model demo code, using a lightweight command.
    Returns:
        1.0  if runs successfully,
        0.5  if times out / partial success,
        0.0  if no instructions or crash.
    """
    meta = pkg.meta or {}
    run_cmd = meta.get("how_to_run") or meta.get("run") or meta.get("script")

    if not run_cmd:
        return 0.0

    run_cmd = str(run_cmd).strip().strip('"').strip("'")
    forbidden = ("rm ", "del ", "shutdown", "format", ":(){:|:&};:")
    if any(x in run_cmd.lower() for x in forbidden):
        return 0.0

    try:
        # use a temp working dir to avoid clobbering local files
        cwd = Path(os.getcwd()) / "tmp_repro"
        cwd.mkdir(exist_ok=True)

        # On Windows, simple commands like "echo hello" are shell builtins,
        # so shell=True avoids unnecessary failures.
        proc = subprocess.run(
            run_cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )
        if proc.returncode == 0:
            return 1.0
        # Non-zero but produced some output and not a Python traceback → partial
        if proc.stdout or "Traceback" not in (proc.stderr or ""):
            return 0.5
        return 0.0
    except subprocess.TimeoutExpired:
        return 0.5
    except Exception:
        return 0.0


# ---------------- Reviewedness (WRAPPERS you need) ----------------
def metric_reviewedness_from_meta(meta: Optional[dict]) -> Tuple[float, str]:
    """
    Returns (score, rationale) for the Reviewedness metric.
    Looks for meta['repo_url'] (preferred), falling back to common aliases.
    """
    if not meta:
        return 0.0, "No metadata found."

    # normalize to repo_url if the uploader used other keys
    repo_url = (
        meta.get("repo_url")
        or meta.get("repo")
        or meta.get("github")
        or meta.get("github_url")
    )
    if not repo_url:
        return 0.0, "meta.repo_url not provided."

    return reviewedness_score(repo_url, lookback_days=90)


def metric_reviewedness(meta: Optional[dict]) -> float:
    """Convenience: return just the numeric score."""
    s, _ = metric_reviewedness_from_meta(meta)
    return s


# ---------------- Unified scoring adapter ----------------
def rate_model(pkg: ModelPackage) -> Scores:
    """
    Unified scoring adapter combining all metrics.
    Adjust these defaults and weights as your rubric requires.
    """
    scores = {
        "availability": 0.8,
        "bus_factor": 0.7,
        "code_quality": 0.65,
        "dataset_quality": 0.75,
        "ramp_up": 0.6,
        "license": 0.9,
        "latency": 0.8,
    }

    # Reproducibility metric
    scores["reproducibility"] = run_reproducibility_check(pkg)

    # Reviewedness metric (numeric only here; notes are returned by the API)
    rev_score, rev_note = metric_reviewedness_from_meta(pkg.meta or {})
    scores["reviewedness"] = rev_score
    # Do NOT mutate pkg.meta here; the API can include rev_note in its response.

    # Treescore (placeholder until lineage is finalized)
    scores["treescore"] = 0.7

    return Scores(**scores)
