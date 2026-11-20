import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from unittest import mock

from instagram.automation.http import make_handler


class AutomationHttpTests(unittest.TestCase):
    def setUp(self):
        self.handler = make_handler(automation_token="tok", client_factory=lambda: mock.Mock())
        self.httpd = HTTPServer(("127.0.0.1", 0), self.handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health(self):
        with urllib.request.urlopen(self._url("/health")) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(resp.read()), {"ok": True})

    def test_publish_requires_auth(self):
        req = urllib.request.Request(
            self._url("/v1/publish"),
            data=b'{"type":"image","image_url":"https://a.jpg"}',
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 401)

    def test_publish_ok(self):
        with mock.patch(
            "instagram.automation.http.jobs.run_job",
            return_value={"ok": True, "type": "image", "result": {"id": "9"}},
        ):
            body = json.dumps({"type": "image", "image_url": "https://a.jpg"}).encode()
            req = urllib.request.Request(
                self._url("/v1/publish"),
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer tok",
                },
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(json.loads(resp.read())["result"]["id"], "9")


if __name__ == "__main__":
    unittest.main()
