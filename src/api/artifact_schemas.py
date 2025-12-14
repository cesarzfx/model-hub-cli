# src/api/artifact_schemas.py
from pydantic import BaseModel
from typing import List, Optional
import re

# Valid artifact types from the spec
VALID_TYPES = {"model", "dataset", "code"}

# Pattern for ArtifactID (OpenAPI spec)
ARTIFACT_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]+$")


class ArtifactData(BaseModel):
    url: str
    download_url: Optional[str] = None
    name: Optional[str] = None


class ArtifactMetadata(BaseModel):
    name: str
    id: str
    type: str


class ArtifactQuery(BaseModel):
    name: str
    types: Optional[List[str]] = None


class Artifact(BaseModel):
    metadata: ArtifactMetadata
    data: ArtifactData


class ArtifactRegEx(BaseModel):
    regex: str


class ArtifactCostEntry(BaseModel):
    standalone_cost: Optional[float] = None
    total_cost: float
