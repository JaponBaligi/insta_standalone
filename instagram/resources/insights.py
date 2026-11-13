"""IG insights: account- and media-level metrics via Graph API."""
from __future__ import annotations

from typing import Any, Optional, Sequence, Union

from ..client import GraphClient

MetricsArg = Union[str, Sequence[str]]


def _require(name: str, value: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _metric_param(metrics: MetricsArg) -> str:
    if isinstance(metrics, str):
        metric = metrics.strip()
    else:
        metric = ",".join(str(m).strip() for m in metrics if str(m).strip())
    if not metric:
        raise ValueError("metrics is required")
    return metric


def get_account_insights(
    client: GraphClient,
    metrics: MetricsArg,
    *,
    period: str = "day",
    since: Optional[int] = None,
    until: Optional[int] = None,
    metric_type: Optional[str] = None,
    breakdown: Optional[str] = None,
) -> dict[str, Any]:
    """GET /{ig-user-id}/insights — pass Meta metric names as needed."""
    params: dict[str, Any] = {
        "metric": _metric_param(metrics),
        "period": period,
    }
    if since is not None:
        params["since"] = since
    if until is not None:
        params["until"] = until
    if metric_type is not None:
        params["metric_type"] = metric_type
    if breakdown is not None:
        params["breakdown"] = breakdown
    return client.get(f"{client.node}/insights", **params)


def get_media_insights(
    client: GraphClient,
    media_id: str,
    metrics: MetricsArg,
    *,
    period: Optional[str] = None,
) -> dict[str, Any]:
    """GET /{ig-media-id}/insights."""
    media_id = _require("media_id", media_id)
    params: dict[str, Any] = {"metric": _metric_param(metrics)}
    if period is not None:
        params["period"] = period
    return client.get(f"{media_id}/insights", **params)
