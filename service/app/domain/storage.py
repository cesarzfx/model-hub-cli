# service/app/domain/storage.py
import os
import shutil
from dataclasses import dataclass
from typing import Optional
from ..core.config import get_settings

# Optional: import boto3 safely
try:
    import boto3
except ImportError:
    boto3 = None


# ---------------------------------------------------------
# Base class (must come first!)
# ---------------------------------------------------------
class BlobStore:
    def put(self, key: str, file_path: str) -> str:
        """Upload a file and return its key."""
        raise NotImplementedError

    def get_path(self, key: str) -> str:
        """Return a local path to the blob."""
        raise NotImplementedError


# ---------------------------------------------------------
# Local filesystem implementation
# ---------------------------------------------------------
@dataclass
class LocalBlobStore(BlobStore):
    root: str

    def put(self, key: str, file_path: str) -> str:
        dst = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(file_path, dst)
        return key

    def get_path(self, key: str) -> str:
        return os.path.join(self.root, key)


# ---------------------------------------------------------
# AWS S3 implementation
# ---------------------------------------------------------
@dataclass
class S3BlobStore(BlobStore):
    bucket: str
    region: str | None = None
    cache_root: str = "/tmp/s3cache"

    def __post_init__(self):
        if boto3 is None:
            raise RuntimeError("boto3 not installed; run `pip install boto3`")
        self.client = boto3.client("s3", region_name=self.region)
        os.makedirs(self.cache_root, exist_ok=True)

    def put(self, key: str, file_path: str) -> str:
        self.client.upload_file(file_path, self.bucket, key)
        return key

    def get_path(self, key: str) -> str:
        # Download into a local cache if not already there
        local = os.path.join(self.cache_root, key.replace("/", "_"))
        if not os.path.exists(local):
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, "wb") as f:
                self.client.download_fileobj(self.bucket, key, f)
        return local


# ---------------------------------------------------------
# Factory / global getter
# ---------------------------------------------------------
_blob_instance: BlobStore | None = None

def get_blob_store() -> BlobStore:
    """Return the active blob store instance (local or S3)."""
    global _blob_instance
    if _blob_instance:
        return _blob_instance

    s = get_settings()
    if s.STORAGE_BACKEND == "local":
        os.makedirs(s.BLOB_ROOT, exist_ok=True)
        _blob_instance = LocalBlobStore(s.BLOB_ROOT)
    elif s.STORAGE_BACKEND == "s3":
        if not s.S3_BUCKET:
            raise RuntimeError("S3 backend selected but S3_BUCKET is not set")
        _blob_instance = S3BlobStore(bucket=s.S3_BUCKET, region=s.AWS_REGION)
    else:
        raise NotImplementedError(f"Unknown STORAGE_BACKEND={s.STORAGE_BACKEND}")
    return _blob_instance
