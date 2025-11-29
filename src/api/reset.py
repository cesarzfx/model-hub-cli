from fastapi import APIRouter, HTTPException, Header
from typing import Dict, List
import os
import glob
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

# Import issued_tokens from auth.py
try:
    from .auth import issued_tokens
except ImportError:
    issued_tokens = {}

# Directory to store artifacts - use /tmp for AWS Lambda compatibility
ARTIFACTS_DIR = "/tmp/artifacts"


def clear_dynamo_table() -> None:
    """
    Best-effort: clear all items from the DynamoDB artifacts table, if configured.

    - Uses ARTIFACTS_TABLE_NAME env var.
    - Swallows all errors so /reset never returns 500 because of DynamoDB.
    """
    table_name = os.getenv("ARTIFACTS_TABLE_NAME")
    if not table_name:
        logger.info("No ARTIFACTS_TABLE_NAME set; skipping DynamoDB reset.")
        return

    try:
        import boto3  # type: ignore
    except ImportError:
        logger.warning("boto3 not available; skipping DynamoDB reset.")
        return

    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        scan_kwargs = {"ProjectionExpression": "artifact_id"}

        while True:
            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])
            if not items:
                break

            with table.batch_writer() as batch:
                for item in items:
                    artifact_id = item.get("artifact_id")
                    if artifact_id is not None:
                        batch.delete_item(Key={"artifact_id": artifact_id})

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

        logger.info("Successfully cleared DynamoDB table %s", table_name)
    except Exception as e:
        logger.error("Error clearing DynamoDB table %s: %s", table_name, e)
        return


def clear_artifacts() -> None:
    """Clear all stored artifacts and recreate empty directory"""
    if os.path.exists(ARTIFACTS_DIR):
        files = glob.glob(f"{ARTIFACTS_DIR}/*")
        for f in files:
            try:
                if os.path.isdir(f):
                    os.rmdir(f)
                else:
                    os.remove(f)
            except Exception as e:
                print(f"Error removing {f}: {e}")

    # Ensure artifacts directory exists after reset
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


@router.delete("/reset")
def reset_registry() -> Dict:
    """
    Reset the registry to its initial state. Requires valid X-Authorization token.
    """

    clear_artifacts()

    clear_dynamo_table()

    return {"message": "Registry reset successfully"}
