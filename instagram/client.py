#client.py
import logging
import time
import warnings
from typing import Any, Optional

import requests

from . import token_store
from .config import Config, load_config
from .exceptions import GraphAPIError

REFRESH_THRESHOLD_SECONDS = 7 * 24 * 3600

log = logging.getLogger(__name__)


class GraphClient:
    
    def __init__(
        self,
        config: Optional[Config] = None,
        timeout: int = 60,
        auto_refresh: bool = True,
    ):
        self.config = config or load_config()
        self.timeout = timeout
        self.auto_refresh = auto_refresh
        self.session = requests.Session()

        self._busy = False 
        self._expiry_checked = False

        stored = token_store.load()
        # .env token is only the bootstrap; once a token is stored (and kept
        # fresh by auto-refresh) the stored one wins on purpose.
        self._token = stored["access_token"] if stored else self.config.access_token
        log.info("Token source: %s", "token/.token.json" if stored else ".env (bootstrap)")

    @property
    def node(self) -> str:
        """The account the requests act on (Instagram account ID)."""
        return self.config.node

    @property
    def token(self) -> str:
        return self._token

    def get(self, path: str, **params: Any) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, **data: Any) -> dict:
        return self._request("POST", path, data=data)

    def delete(self, path: str, **params: Any) -> dict:
        return self._request("DELETE", path, params=params)

    def _ensure_fresh_token(self) -> None:
        if not self.auto_refresh or self._busy:
            return
        if not (self.config.app_id and self.config.app_secret):
            return

        self._busy = True
        try:
            stored = token_store.load()
            if stored is None and not self._expiry_checked:
                self._expiry_checked = True
                stored = self._learn_expiry()

            left = token_store.seconds_left(stored)
            if left is not None and left < REFRESH_THRESHOLD_SECONDS:
                self._refresh()
        except GraphAPIError as exc:
            warnings.warn(f"Automatic token refresh failed: {exc}")
        finally:
            self._busy = False

    def _learn_expiry(self) -> dict:
        """Ask Meta when the current token expires and store it."""
        app_token = f"{self.config.app_id}|{self.config.app_secret}"
        info = self.get(
            "debug_token",
            input_token=self._token,
            access_token=app_token,
        ).get("data", {})

        expires_at = info.get("expires_at") or 0
        expires_in = expires_at - int(time.time()) if expires_at else None
        return token_store.save(self._token, expires_in)

    def _refresh(self) -> None:
        """Exchange the current token for a new long-lived one."""
        result = self.get(
            "oauth/access_token",
            grant_type="fb_exchange_token",
            client_id=self.config.app_id,
            client_secret=self.config.app_secret,
            fb_exchange_token=self._token,
        )
        self._token = result["access_token"]
        token_store.save(self._token, result.get("expires_in"))

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> dict:
        self._ensure_fresh_token()

        url = f"{self.config.base_url}/{path.lstrip('/')}"

        params = self._clean(params)
        data = self._clean(data)

        params.setdefault("access_token", self._token)

        response = self.session.request(
            method,
            url,
            params=params,
            data=data or None,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    @staticmethod
    def _clean(values: Optional[dict]) -> dict:
        """Drop None values and convert booleans to the strings the API expects."""
        cleaned = {}
        for key, value in (values or {}).items():
            if value is None:
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _handle_response(response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if not response.ok:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            raise GraphAPIError(
                status_code=response.status_code,
                message=error.get("message") or response.text or "Unknown error",
                code=error.get("code"),
                subcode=error.get("error_subcode"),
                fbtrace_id=error.get("fbtrace_id"),
            )

        return payload