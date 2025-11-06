# service/app/domain/cli_adapter.py
"""
Adapter to convert ModelPackage to ModelData interface for CLI metrics.
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to access CLI src module
# This allows imports from src/ when running from service/ directory
_current_dir = Path(__file__).parent
_service_dir = _current_dir.parent.parent
_project_root = _service_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from .models import ModelPackage
from src.ModelData import ModelData
from src.util.metadata_fetchers import HuggingFaceFetcher, GitHubFetcher, DatasetFetcher


class ModelPackageAdapter:
    """
    Adapter that makes ModelPackage compatible with CLI ModelData interface.
    """
    def __init__(self, pkg: ModelPackage, model_url: Optional[str] = None, 
                 code_url: Optional[str] = None, dataset_url: Optional[str] = None):
        self.pkg = pkg
        self._model_url = model_url or pkg.meta.get("model_url") or pkg.meta.get("hf_id")
        self._code_url = code_url or pkg.meta.get("code_url") or pkg.meta.get("github_url") or pkg.meta.get("repo_url")
        self._dataset_url = dataset_url or pkg.meta.get("dataset_url")
        
        # Metadata caches
        self._hf_metadata: Optional[Dict[str, Any]] = None
        self._github_metadata: Optional[Dict[str, Any]] = None
        self._dataset_metadata: Optional[Dict[str, Any]] = None
        
        # GitHub token
        self._github_token = os.getenv("GITHUB_TOKEN")
    
    @property
    def modelLink(self) -> str:
        """Required model URL"""
        if not self._model_url:
            # Try to construct from name if it looks like HF format
            if "/" in self.pkg.name:
                return f"https://huggingface.co/{self.pkg.name}"
            return f"https://huggingface.co/{self.pkg.name}"
        return self._model_url
    
    @property
    def codeLink(self) -> Optional[str]:
        """Optional code repository URL"""
        return self._code_url
    
    @property
    def datasetLink(self) -> Optional[str]:
        """Optional dataset URL"""
        return self._dataset_url
    
    @property
    def hf_metadata(self) -> Dict[str, Any]:
        """Cached HuggingFace metadata"""
        if self._hf_metadata is None:
            try:
                fetcher = HuggingFaceFetcher()
                if self.modelLink:
                    self._hf_metadata = fetcher.fetch(self.modelLink) or {}
            except Exception:
                self._hf_metadata = {}
        return self._hf_metadata or {}
    
    @property
    def github_metadata(self) -> Dict[str, Any]:
        """Cached GitHub metadata"""
        if self._github_metadata is None and self.codeLink:
            try:
                fetcher = GitHubFetcher(token=self._github_token)
                self._github_metadata = fetcher.fetch(self.codeLink) or {}
            except Exception:
                self._github_metadata = {}
        return self._github_metadata or {}
    
    @property
    def dataset_metadata(self) -> Dict[str, Any]:
        """Cached dataset metadata"""
        if self._dataset_metadata is None and self.datasetLink:
            try:
                fetcher = DatasetFetcher()
                self._dataset_metadata = fetcher.fetch(self.datasetLink) or {}
            except Exception:
                self._dataset_metadata = {}
        return self._dataset_metadata or {}
    
    # Expose private attributes for metrics that access them directly
    def __getattr__(self, name: str):
        if name == "_hf_metadata":
            return self.hf_metadata
        if name == "_github_metadata":
            return self.github_metadata
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

