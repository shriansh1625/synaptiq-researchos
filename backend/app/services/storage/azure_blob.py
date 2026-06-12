"""Azure Blob Storage helpers for production artifact persistence."""

from __future__ import annotations

from pathlib import Path

from config.settings import get_settings


def upload_artifact(local_path: Path, *, blob_name: str) -> str | None:
    """Upload a local artifact to Azure Blob Storage when configured."""
    settings = get_settings()
    connection = settings.azure_storage_connection_string
    if not connection or not local_path.is_file():
        return None

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        return None

    container = "synaptiq-artifacts"
    client = BlobServiceClient.from_connection_string(connection)
    container_client = client.get_container_client(container)
    try:
        container_client.create_container()
    except Exception:
        pass

    blob_client = container_client.get_blob_client(blob_name)
    with local_path.open("rb") as handle:
        blob_client.upload_blob(handle, overwrite=True)
    return blob_client.url
