#publisher.py
import time
from typing import Any, Optional

from .client import GraphClient
from .exceptions import MediaProcessingError, MediaTimeoutError


def create_container(client: GraphClient, **params: Any) -> str:
    """Create a media container and return its ID.

    None values are dropped automatically, so optional fields can be passed as-is.
    """
    result = client.post(f"{client.node}/media", **params)
    return result["id"]


def wait_until_ready(
    client: GraphClient,
    container_id: str,
    timeout: int = 300,
    interval: int = 5,
) -> None:
    """Poll the container until Instagram finishes processing it."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        info = client.get(container_id, fields="status_code,status")
        status_code = info.get("status_code")

        if status_code in ("FINISHED", "PUBLISHED"):
            return
        if status_code in ("ERROR", "EXPIRED"):
            raise MediaProcessingError(
                f"Container {container_id} failed: {info.get('status') or status_code}"
            )

        time.sleep(interval)

    raise MediaTimeoutError(
        f"Container {container_id} was not ready after {timeout} seconds."
    )


def publish_container(client: GraphClient, container_id: str) -> dict:
    """Publish a finished container and return the created media ID."""
    return client.post(f"{client.node}/media_publish", creation_id=container_id)


def publish_media(
    client: GraphClient,
    timeout: int = 300,
    interval: int = 5,
    **params: Any,
) -> dict:
    """Full flow: create container -> wait until ready -> publish."""
    container_id = create_container(client, **params)
    wait_until_ready(client, container_id, timeout=timeout, interval=interval)
    return publish_container(client, container_id)