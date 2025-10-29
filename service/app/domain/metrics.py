# service/app/domain/metrics.py
import subprocess
import os
from pathlib import Path
from .models import ModelPackage
from .schemas import Scores
from ..integrations.github import reviewedness_score

def run_reproducibility_check(pkg: ModelPackage, timeout: int = 10) -> float:
    """
    Try to reproduce model demo code.
    Returns:
        1.0  if runs successfully,
        0.5  if run partially succeeds or fails gracefully,
        0.0  if no instructions or crash.
    """
    # Heuristic: look for a run command or script name in metadata
    meta = pkg.meta or {}
    run_cmd = meta.get("how_to_run") or meta.get("run") or meta.get("script")

    # No script -> cannot reproduce
    if not run_cmd:
        return 0.0

    # Normalize and validate (avoid destructive commands)
    run_cmd = str(run_cmd).strip()
    forbidden = ["rm ", "del ", "shutdown", "format"]
    if any(x in run_cmd.lower() for x in forbidden):
        return 0.0

    try:
        # Use a temporary working directory to avoid clobbering local files
        cwd = Path(os.getcwd()) / "tmp_repro"
        cwd.mkdir(exist_ok=True)

        # Run the command in a subprocess
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
        else:
            # Non-zero exit code but produced output -> partial success
            if proc.stdout or "Traceback" not in proc.stderr:
                return 0.5
            return 0.0

    except subprocess.TimeoutExpired:
        # Execution hung -> treat as partial
        return 0.5
    except Exception:
        return 0.0


def rate_model(pkg: ModelPackage) -> Scores:
    """
    Unified scoring adapter combining all metrics.
    Currently mixes Phase 1 metrics (stubbed) + new ones.
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

    # Reviewedness metric (GitHub API)
    repo_url = (pkg.meta or {}).get("repo") or (pkg.meta or {}).get("github")
    if repo_url:
        r_score, why = reviewedness_score(repo_url, lookback_days=90)
        scores["reviewedness"] = r_score
        pkg.meta["reviewedness_note"] = why
    else:
        scores["reviewedness"] = 0.0

    # Treescore (placeholder; will be refined in Step 3)
    scores["treescore"] = 0.7

    return Scores(**scores)
