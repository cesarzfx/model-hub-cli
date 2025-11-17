from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional
import os
import json

router = APIRouter()

ARTIFACTS_DIR = "/tmp/artifacts"


class ArtifactData(BaseModel):
    url: HttpUrl


class ArtifactMetadata(BaseModel):
    name: str
    id: str
    types: List[str]


class ArtifactQuery(BaseModel):
    name: str


class Artifact(BaseModel):
    metadata: ArtifactMetadata
    data: ArtifactData


def store_artifact(artifact_id: str, data: dict) -> None:
    """Store artifact data in the filesystem"""
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)

    filepath = os.path.join(ARTIFACTS_DIR, f"{artifact_id}.json")
    with open(filepath, "w") as f:
        json.dump(data, f)


def get_stored_artifact(artifact_id: str) -> Optional[dict]:
    """Retrieve artifact data from filesystem"""
    filepath = os.path.join(ARTIFACTS_DIR, f"{artifact_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            # If data is not a dict, wrap it in one for safety
            return {"metadata": {}, "data": data}
    return None


@router.post("/artifacts")
def list_artifacts(query: List[ArtifactQuery]) -> Dict:
    """List all artifacts matching the query"""
    artifacts = []
    if not os.path.exists(ARTIFACTS_DIR):
        return {"artifacts": []}
    if not query or len(query) == 0:
        return {"artifacts": []}
    if query and query[0].name == "*":
        # Return all artifacts
        for filename in os.listdir(ARTIFACTS_DIR):
            if filename.endswith(".json"):
                artifact_id = filename[:-5]  # Remove .json
                stored = get_stored_artifact(artifact_id)
                if stored and isinstance(stored.get("metadata"), dict):
                    artifacts.append(stored["metadata"])
    else:
        # Return artifacts matching names
        for q in query:
            for filename in os.listdir(ARTIFACTS_DIR):
                if filename.endswith(".json"):
                    stored = get_stored_artifact(filename[:-5])
                    if (
                        stored
                        and isinstance(stored.get("metadata"), dict)
                        and stored["metadata"].get("name") == q.name
                    ):
                        artifacts.append(stored["metadata"])

    return {"artifacts": artifacts}


@router.post("/artifact/{artifact_type}")
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Dict:
    """Create a new artifact"""
    # Generate a simple ID (in production this would be more sophisticated)
    import hashlib

    artifact_id = hashlib.md5(str(artifact.url).encode()).hexdigest()[:10]

    # Create artifact object
    artifact_obj = Artifact(
        metadata=ArtifactMetadata(
            name=str(artifact.url).split("/")[-1], id=artifact_id, types=[artifact_type]
        ),
        data=artifact,
    )

    # Store artifact
    store_artifact(artifact_id, artifact_obj.dict())

    # Return the full artifact object as dict (not just metadata)
    return artifact_obj.dict()


@router.get("/artifact/{artifact_type}/{id}")
def get_artifact(artifact_type: str, id: str) -> Dict:
    """Get artifact by ID"""
    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if stored["metadata"]["type"] != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")
    return stored


@router.delete("/artifact/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> Dict:
    """Delete an artifact"""
    filepath = os.path.join(ARTIFACTS_DIR, f"{id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Verify type matches before deleting
    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if stored["metadata"]["type"] != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    os.remove(filepath)
    return {"message": "Artifact deleted"}


@router.put("/artifact/{artifact_type}/{id}")
def update_artifact(
    artifact_type: str,
    id: str,
    artifact: ArtifactData,
) -> Dict:
    """Update an existing artifact"""
    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if stored["metadata"]["type"] != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    # Update artifact
    stored["data"] = artifact.dict()
    store_artifact(id, stored)

    return stored
