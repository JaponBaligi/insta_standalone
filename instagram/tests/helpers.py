"""Shared test helpers (stdlib only; works with unittest and pytest)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from instagram import token_store
from instagram.config import Config


def make_config(**overrides):
    values = dict(
        access_token="TOKEN",
        node="1784",
        api_version="v25.0",
        app_id="",
        app_secret="",
    )
    values.update(overrides)
    return Config(**values)


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, payload=None, text="", json_error=False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error
        self.text = text
        self.ok = 200 <= status_code < 400

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


class FakeClient:
    """Records calls and returns scripted responses (stand-in for GraphClient).

    routes: {("POST", "1784/media"): {"id": "c1"}}
    A list value is consumed in order (the last item repeats).
    A callable value is called with the recorded kwargs.
    """

    def __init__(self, routes=None, node="1784", app_id="", app_secret="", token="TOKEN"):
        self.node = node
        self.config = SimpleNamespace(app_id=app_id, app_secret=app_secret)
        self._token = token
        self.routes = dict(routes or {})
        self.calls = []

    @property
    def token(self):
        return self._token

    def _dispatch(self, method, path, params):
        self.calls.append((method, path, params))
        key = (method, path)
        if key not in self.routes:
            raise AssertionError(f"Unexpected call: {key} {params}")
        value = self.routes[key]
        if callable(value):
            return value(**params)
        if isinstance(value, list):
            item = value.pop(0) if len(value) > 1 else value[0]
        else:
            item = value
        if isinstance(item, Exception):
            raise item
        return item

    def get(self, path, **params):
        return self._dispatch("GET", path, params)

    def post(self, path, **data):
        return self._dispatch("POST", path, data)

    def delete(self, path, **params):
        return self._dispatch("DELETE", path, params)

    def calls_for(self, method, path):
        return [p for m, pa, p in self.calls if (m, pa) == (method, path)]


class IsolatedTokenStoreTestCase(unittest.TestCase):
    """Redirects token_store.STORE_PATH to a temp dir so the real
    token/.token.json is never read or written by tests."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "token" / ".token.json"
        patcher = mock.patch.object(token_store, "STORE_PATH", self.store_path)
        patcher.start()
        self.addCleanup(patcher.stop)
