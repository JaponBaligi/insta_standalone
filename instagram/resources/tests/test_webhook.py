import hashlib
import hmac
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer

from instagram.webhook import handlers
from instagram.webhook.server import make_handler


def sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class VerifyChallengeTests(unittest.TestCase):
    def test_returns_challenge_when_token_matches(self):
        challenge = handlers.verify_challenge(
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "secret",
                "hub.challenge": "12345",
            },
            verify_token="secret",
        )
        self.assertEqual(challenge, "12345")

    def test_rejects_bad_token_or_mode(self):
        for query in (
            {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"},
            {"hub.mode": "unsubscribe", "hub.verify_token": "secret", "hub.challenge": "1"},
            {"hub.mode": "subscribe", "hub.verify_token": "secret"},
        ):
            with self.assertRaises(ValueError, msg=query):
                handlers.verify_challenge(query, verify_token="secret")


class VerifySignatureTests(unittest.TestCase):
    def test_accepts_valid_signature(self):
        body = b'{"object":"instagram"}'
        self.assertTrue(handlers.verify_signature(body, sign("app", body), "app"))

    def test_rejects_invalid_or_missing(self):
        body = b"{}"
        self.assertFalse(handlers.verify_signature(body, "sha256=dead", "app"))
        self.assertFalse(handlers.verify_signature(body, None, "app"))
        self.assertFalse(handlers.verify_signature(body, "sha256=ab", ""))


class ParseEventsTests(unittest.TestCase):
    def test_flattens_changes(self):
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "ig1",
                    "time": 99,
                    "changes": [
                        {"field": "comments", "value": {"id": "c1"}},
                        {"field": "mentions", "value": {"id": "m1"}},
                    ],
                }
            ],
        }
        events = handlers.parse_events(payload)
        self.assertEqual(
            events,
            [
                {
                    "object": "instagram",
                    "field": "comments",
                    "value": {"id": "c1"},
                    "id": "ig1",
                    "time": 99,
                },
                {
                    "object": "instagram",
                    "field": "mentions",
                    "value": {"id": "m1"},
                    "id": "ig1",
                    "time": 99,
                },
            ],
        )

    def test_include_filter_and_messaging(self):
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "ig1",
                    "time": 1,
                    "changes": [{"field": "comments", "value": {}}],
                    "messaging": [{"sender": {"id": "u1"}, "message": {"text": "hi"}}],
                }
            ],
        }
        events = handlers.parse_events(payload, include={"messages"})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["field"], "messages")
        self.assertEqual(events[0]["value"]["sender"]["id"], "u1")

    def test_empty_payload(self):
        self.assertEqual(handlers.parse_events({}), [])
        self.assertEqual(handlers.parse_events({"entry": []}), [])


class WebhookServerTests(unittest.TestCase):
    def setUp(self):
        self.received = []
        handler = make_handler(
            verify_token="tok",
            app_secret="sec",
            on_event=self.received.append,
            include={"comments"},
        )
        self.httpd = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _url(self, path="/webhook"):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_get_verification(self):
        qs = urllib.parse.urlencode(
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "tok",
                "hub.challenge": "42",
            }
        )
        with urllib.request.urlopen(f"{self._url()}?{qs}") as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read().decode(), "42")

    def test_post_signed_event(self):
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "ig1",
                    "time": 5,
                    "changes": [{"field": "comments", "value": {"text": "x"}}],
                }
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(),
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sign("sec", body),
            },
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["field"], "comments")

    def test_post_bad_signature_rejected(self):
        body = b'{"object":"instagram","entry":[]}'
        req = urllib.request.Request(
            self._url(),
            data=body,
            method="POST",
            headers={"X-Hub-Signature-256": "sha256=00"},
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 403)


class PackageImportTests(unittest.TestCase):
    def test_package_exports(self):
        import instagram.webhook as wh
        import instagram.webhook.server as srv

        self.assertTrue(callable(wh.verify_challenge))
        self.assertTrue(callable(wh.verify_signature))
        self.assertTrue(callable(wh.parse_events))
        self.assertTrue(callable(srv.serve_forever))


if __name__ == "__main__":
    unittest.main()
