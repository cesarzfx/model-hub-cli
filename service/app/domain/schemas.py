# service/app/domain/schemas.py
from pydantic import BaseModel, Field, AnyUrl
from typing import Dict, List, Optional, Literal

Score = float

class Scores(BaseModel):
    availability: Score | None = None
    bus_factor: Score | None = None
    code_quality: Score | None = None
    dataset_quality: Score | None = None
    ramp_up: Score | None = None
    license: Score | None = None
    reproducibility: Score | None = None
    reviewedness: Score | None = None
    treescore: Score | None = None
    latency: Score | None = None

class PackageCreate(BaseModel):
    name: str
    version: str
    card_text: str | None = None
    meta: Dict[str, str] | None = None
    parents: List[str] = []
    sensitive: bool = False
    pre_download_hook: str | None = None  # JS path inside package

class PackageSummary(BaseModel):
    id: str
    name: str
    version: str
    size_bytes: int
    scores: Scores

class PackageDetail(PackageSummary):
    card_text: str | None = None
    meta: Dict[str, str] | None = None
    parents: List[str] = []

class PackagePage(BaseModel):
    page: int
    limit: int
    total: int
    items: List[PackageSummary]

class RateRequest(BaseModel):
    id: str

class IngestRequest(BaseModel):
    hf_id: str

class IngestResult(BaseModel):
    id: str
    name: str
    version: str
    scores: Scores

class LicenseCheckRequest(BaseModel):
    github_url: AnyUrl
    model_id: str

class LicenseCheckResult(BaseModel):
    ok: bool
    rationale: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResult(BaseModel):
    token: str
