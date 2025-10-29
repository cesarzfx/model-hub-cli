# service/app/domain/models.py
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ModelPackage:
    id: str
    name: str
    version: str
    card_text: str | None
    meta: Dict[str, str]
    parents: List[str]
    sensitive: bool
    pre_download_hook: str | None
    size_bytes: int = 0
    scores: Dict[str, float] = field(default_factory=dict)
    blob_key_full: str | None = None
    blob_key_weights: str | None = None
    blob_key_datasets: str | None = None
