import time
import unittest
import warnings
from unittest import mock

from instagram import client as client_module
from instagram import token_store
from instagram.client import REFRESH_THRESHOLD_SECONDS, GraphClient
from instagram.exceptions import GraphAPIError
from instagram.tests.helpers import (
    FakeResponse,
    IsolatedTokenStoreTestCase,
    make_config,
)


def make_client(session_responses=None, **config_overrides):
    c = GraphClient(config=make_config(**config_overrides))
    c.session = mock.Mock()
    if session_responses is not None:
        c.session.request.side_effect = session_responses
    else:
        c.session.request.return_value = FakeResponse(200, {"ok": True})
    return c


class InitTests(IsolatedTokenStoreTestCase):
    def test_uses_config_token_when_nothing_stored(self):
        c = GraphClient(config=make_config(access_token="ENV"))
        self.assertEqual(c.token, "ENV")

    def test_stored_token_wins_over_config(self):
        token_store.save("STORED", 10_000_000)
        c = GraphClient(config=make_config(access_token="ENV"))
        self.assertEqual(c.token, "STORED")

    def test_node_property(self):
        self.assertEqual(GraphClient(config=make_config(node="42")).node, "42")

    def test_loads_config_when_not_given(self):
        with mock.patch.object(client_module, "load_config", return_value=make_config(node="7")):
            self.assertEqual(GraphClient().node, "7")


class RequestTests(IsolatedTokenStoreTestCase):
    def test_get_builds_url_and_passes_token(self):
        c = make_client()
        c.get("1784", fields="id")
        args, kwargs = c.session.request.call_args
        self.assertEqual(args, ("GET", "https://graph.facebook.com/v25.0/1784"))
        self.assertEqual(kwargs["params"], {"fields": "id", "access_token": "TOKEN"})
        self.assertIsNone(kwargs["data"])
        self.assertEqual(kwargs["timeout"], 60)

    def test_leading_slash_in_path_is_stripped(self):
        c = make_client()
        c.get("/me")
        self.assertEqual(c.session.request.call_args[0][1], "https://graph.facebook.com/v25.0/me")

    def test_post_sends_form_data(self):
        c = make_client()
        c.post("1784/media", image_url="u", caption=None)
        _, kwargs = c.session.request.call_args
        self.assertEqual(c.session.request.call_args[0][0], "POST")
        self.assertEqual(kwargs["data"], {"image_url": "u"})
        self.assertEqual(kwargs["params"], {"access_token": "TOKEN"})

    def test_post_with_only_none_values_sends_no_body(self):
        c = make_client()
        c.post("x", a=None)
        self.assertIsNone(c.session.request.call_args[1]["data"])

    def test_delete_uses_params(self):
        c = make_client()
        c.delete("999")
        self.assertEqual(c.session.request.call_args[0][0], "DELETE")

    def test_explicit_access_token_is_not_overridden(self):
        c = make_client()
        c.get("debug_token", access_token="APP|SECRET")
        self.assertEqual(c.session.request.call_args[1]["params"]["access_token"], "APP|SECRET")

    def test_custom_timeout(self):
        c = GraphClient(config=make_config(), timeout=5)
        c.session = mock.Mock()
        c.session.request.return_value = FakeResponse(200, {})
        c.get("x")
        self.assertEqual(c.session.request.call_args[1]["timeout"], 5)

    def test_returns_json_payload(self):
        c = make_client([FakeResponse(200, {"id": "1"})])
        self.assertEqual(c.get("x"), {"id": "1"})


class CleanTests(unittest.TestCase):
    def test_drops_none_and_converts_bool(self):
        self.assertEqual(
            GraphClient._clean({"a": None, "b": True, "c": False, "d": 0, "e": ""}),
            {"b": "true", "c": "false", "d": 0, "e": ""},
        )

    def test_none_input(self):
        self.assertEqual(GraphClient._clean(None), {})


class HandleResponseTests(unittest.TestCase):
    def test_success_with_non_json_body_returns_empty_dict(self):
        self.assertEqual(GraphClient._handle_response(FakeResponse(200, json_error=True)), {})

    def test_error_parses_graph_error_body(self):
        resp = FakeResponse(
            400,
            {"error": {"message": "Bad", "code": 100, "error_subcode": 2, "fbtrace_id": "t"}},
        )
        with self.assertRaises(GraphAPIError) as cm:
            GraphClient._handle_response(resp)
        e = cm.exception
        self.assertEqual((e.status_code, e.message, e.code, e.subcode, e.fbtrace_id),
                         (400, "Bad", 100, 2, "t"))

    def test_error_falls_back_to_text(self):
        with self.assertRaises(GraphAPIError) as cm:
            GraphClient._handle_response(FakeResponse(502, json_error=True, text="Bad gateway"))
        self.assertEqual(cm.exception.message, "Bad gateway")

    def test_error_unknown_when_no_info(self):
        with self.assertRaises(GraphAPIError) as cm:
            GraphClient._handle_response(FakeResponse(500, json_error=True, text=""))
        self.assertEqual(cm.exception.message, "Unknown error")

    def test_error_with_non_dict_payload(self):
        with self.assertRaises(GraphAPIError) as cm:
            GraphClient._handle_response(FakeResponse(400, ["weird"], text="raw"))
        self.assertEqual(cm.exception.message, "raw")

    def test_http_error_propagates_through_request(self):
        c = make_client([FakeResponse(401, {"error": {"message": "expired", "code": 190}})])
        with self.assertRaises(GraphAPIError) as cm:
            c.get("me")
        self.assertEqual(cm.exception.code, 190)


class AutoRefreshTests(IsolatedTokenStoreTestCase):
    """_ensure_fresh_token / _learn_expiry / _refresh."""

    def test_no_refresh_without_app_credentials(self):
        c = make_client()
        c.get("x")
        self.assertEqual(c.session.request.call_count, 1)
        self.assertFalse(self.store_path.exists())

    def test_no_refresh_when_auto_refresh_disabled(self):
        c = GraphClient(config=make_config(app_id="id", app_secret="sec"), auto_refresh=False)
        c.session = mock.Mock()
        c.session.request.return_value = FakeResponse(200, {})
        c.get("x")
        self.assertEqual(c.session.request.call_count, 1)

    def test_first_call_learns_expiry_via_debug_token(self):
        far = int(time.time()) + 30 * 24 * 3600
        c = make_client(
            [FakeResponse(200, {"data": {"expires_at": far}}), FakeResponse(200, {"id": "1"})],
            app_id="id",
            app_secret="sec",
        )
        self.assertEqual(c.get("me"), {"id": "1"})

        first = c.session.request.call_args_list[0]
        self.assertTrue(first[0][1].endswith("/debug_token"))
        self.assertEqual(first[1]["params"]["input_token"], "TOKEN")
        self.assertEqual(first[1]["params"]["access_token"], "id|sec")
        stored = token_store.load()
        self.assertEqual(stored["access_token"], "TOKEN")
        self.assertEqual(stored["expires_at"], far)
        self.assertEqual(c.session.request.call_count, 2)

    def test_expiry_is_only_checked_once(self):
        far = int(time.time()) + 30 * 24 * 3600
        c = make_client(
            [FakeResponse(200, {"data": {"expires_at": far}})] + [FakeResponse(200, {})] * 3,
            app_id="id",
            app_secret="sec",
        )
        # stored file is written after the first call, so later calls read it
        c.get("a")
        c.get("b")
        paths = [call[0][1] for call in c.session.request.call_args_list]
        self.assertEqual(sum(p.endswith("/debug_token") for p in paths), 1)

    def test_non_expiring_token_is_never_refreshed(self):
        c = make_client(
            [FakeResponse(200, {"data": {"expires_at": 0}}), FakeResponse(200, {})],
            app_id="id",
            app_secret="sec",
        )
        c.get("me")
        self.assertIsNone(token_store.load()["expires_at"])
        self.assertEqual(c.session.request.call_count, 2)

    def test_refreshes_when_close_to_expiry(self):
        token_store.save("OLD", REFRESH_THRESHOLD_SECONDS - 100)
        c = make_client(
            [
                FakeResponse(200, {"access_token": "NEW", "expires_in": 5_000_000}),
                FakeResponse(200, {"id": "1"}),
            ],
            app_id="id",
            app_secret="sec",
        )
        self.assertEqual(c.get("me"), {"id": "1"})

        exchange = c.session.request.call_args_list[0]
        self.assertTrue(exchange[0][1].endswith("/oauth/access_token"))
        p = exchange[1]["params"]
        self.assertEqual(p["grant_type"], "fb_exchange_token")
        self.assertEqual(p["client_id"], "id")
        self.assertEqual(p["client_secret"], "sec")
        self.assertEqual(p["fb_exchange_token"], "OLD")

        self.assertEqual(c.token, "NEW")
        self.assertEqual(token_store.load()["access_token"], "NEW")
        # the real request used the new token
        self.assertEqual(c.session.request.call_args_list[1][1]["params"]["access_token"], "NEW")

    def test_no_refresh_when_plenty_of_time_left(self):
        token_store.save("OK", REFRESH_THRESHOLD_SECONDS * 4)
        c = make_client(app_id="id", app_secret="sec")
        c.get("me")
        self.assertEqual(c.session.request.call_count, 1)
        self.assertEqual(c.token, "OK")

    def test_refresh_failure_warns_and_request_still_proceeds(self):
        token_store.save("OLD", 10)
        c = make_client(
            [
                FakeResponse(400, {"error": {"message": "nope", "code": 1}}),
                FakeResponse(200, {"id": "1"}),
            ],
            app_id="id",
            app_secret="sec",
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = c.get("me")
        self.assertEqual(result, {"id": "1"})
        self.assertTrue(any("refresh failed" in str(w.message) for w in caught))
        self.assertEqual(c.token, "OLD")
        self.assertFalse(c._busy)

    def test_busy_flag_prevents_recursion(self):
        c = make_client(app_id="id", app_secret="sec")
        c._busy = True
        c.get("x")
        self.assertEqual(c.session.request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
