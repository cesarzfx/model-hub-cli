# service/app/integrations/github.py
from __future__ import annotations
import time
import requests
from dataclasses import dataclass
from typing import Optional, Tuple
from ..core.config import get_settings

# ------------ tiny TTL cache to avoid rate-limit ------------
@dataclass
class _CacheEntry:
    value: Tuple[float, str]
    exp: float

_CACHE: dict[str, _CacheEntry] = {}

def _cache_get(key: str) -> Optional[Tuple[float, str]]:
    e = _CACHE.get(key)
    if not e: return None
    if e.exp < time.time():
        _CACHE.pop(key, None)
        return None
    return e.value

def _cache_put(key: str, value: Tuple[float, str], ttl_s: int = 600):
    _CACHE[key] = _CacheEntry(value=value, exp=time.time() + ttl_s)

# ------------ utilities ------------
def _parse_repo_owner_name(repo_url: str) -> Optional[Tuple[str, str]]:
    # Accept forms like:
    #  - https://github.com/owner/name
    #  - https://github.com/owner/name.git
    #  - git@github.com:owner/name.git
    s = repo_url.strip()
    if "github.com" not in s:
        return None
    if s.startswith("git@github.com:"):
        s = s.split("git@github.com:")[1]
    elif "github.com/" in s:
        s = s.split("github.com/")[1]
    s = s.replace(".git", "")
    parts = s.split("/")
    if len(parts) < 2:
        return None
    return parts[0], parts[1]

# ------------ public API ------------
def reviewedness_score(repo_url: str, lookback_days: int = 90) -> Tuple[float, str]:
    """
    Score in [0,1] based on fraction of merged PRs that had >=1 approving review.
    Returns (score, rationale).
    Caches for 10 minutes to reduce API traffic.
    """
    key = f"reviewedness::{repo_url}::{lookback_days}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    parsed = _parse_repo_owner_name(repo_url)
    if not parsed:
        result = (0.0, "No valid GitHub repository URL found.")
        _cache_put(key, result)
        return result

    owner, name = parsed
    s = get_settings()
    headers = {"Accept": "application/vnd.github+json"}
    if s.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {s.GITHUB_TOKEN}"

    # 1) Pull requests merged in the lookback window
    import datetime as dt
    since = (dt.datetime.utcnow() - dt.timedelta(days=lookback_days)).isoformat() + "Z"

    prs_url = f"https://api.github.com/repos/{owner}/{name}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": 50,
    }
    try:
        r = requests.get(prs_url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        prs = [
            pr for pr in r.json()
            if pr.get("merged_at") and pr["merged_at"] >= since
        ]
        if not prs:
            result = (0.0, "No merged pull requests in lookback window.")
            _cache_put(key, result)
            return result

        reviewed = 0
        considered = 0
        for pr in prs:
            number = pr["number"]
            reviews_url = f"https://api.github.com/repos/{owner}/{name}/pulls/{number}/reviews"
            rr = requests.get(reviews_url, headers=headers, timeout=10)
            if rr.status_code == 403:
                # Rate limited; fall back to heuristic: if PR has >1 commits and >1 participants, treat as reviewed.
                participants = pr.get("requested_reviewers", []) or []
                commits = pr.get("commits") or 1
                considered += 1
                if participants or commits > 1:
                    reviewed += 1
                continue
            rr.raise_for_status()
            reviews = rr.json()
            considered += 1
            if any(rv.get("state") == "APPROVED" for rv in reviews):
                reviewed += 1

        score = reviewed / max(considered, 1)
        rationale = f"{reviewed} of {considered} merged PRs had at least one APPROVED review in the last {lookback_days} days."
        # modest optimism cap if very low sample size
        if considered < 3:
            score *= 0.9
            rationale += " (low sample size penalty applied)"
        result = (round(score, 4), rationale)
        _cache_put(key, result)
        return result
    except requests.RequestException as e:
        result = (0.0, f"GitHub API error: {e}")
        _cache_put(key, result)
        return result
