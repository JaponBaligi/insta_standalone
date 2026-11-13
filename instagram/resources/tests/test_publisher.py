import unittest
from types import SimpleNamespace
from unittest import mock

from instagram import publisher
from instagram.exceptions import GraphAPIError, MediaProcessingError, MediaTimeoutError
from instagram.tests.helpers import FakeClient


class FakeClock:
    """Replaces publisher.time so polling tests run instantly."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class CreateContainerTests(unittest.TestCase):
    def test_posts_to_media_edge_and_returns_id(self):
        c = FakeClient({("POST", "1784/media"): {"id": "c1"}})
        self.assertEqual(publisher.create_container(c, image_url="u", caption="hi"), "c1")
        self.assertEqual(c.calls[0], ("POST", "1784/media", {"image_url": "u", "caption": "hi"}))

    def test_missing_id_raises_key_error(self):
        c = FakeClient({("POST", "1784/media"): {}})
        with self.assertRaises(KeyError):
            publisher.create_container(c, image_url="u")


class WaitUntilReadyTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        p = mock.patch.object(
            publisher, "time", SimpleNamespace(time=self.clock.time, sleep=self.clock.sleep)
        )
        p.start()
        self.addCleanup(p.stop)

    def test_returns_immediately_when_finished(self):
        c = FakeClient({("GET", "c1"): {"status_code": "FINISHED"}})
        publisher.wait_until_ready(c, "c1")
        self.assertEqual(self.clock.sleeps, [])
        self.assertEqual(c.calls[0][2], {"fields": "status_code,status"})

    def test_published_counts_as_ready(self):
        c = FakeClient({("GET", "c1"): {"status_code": "PUBLISHED"}})
        publisher.wait_until_ready(c, "c1")

    def test_polls_until_finished(self):
        c = FakeClient(
            {("GET", "c1"): [
                {"status_code": "IN_PROGRESS"},
                {"status_code": "IN_PROGRESS"},
                {"status_code": "FINISHED"},
            ]}
        )
        publisher.wait_until_ready(c, "c1", interval=3)
        self.assertEqual(self.clock.sleeps, [3, 3])
        self.assertEqual(len(c.calls), 3)

    def test_error_status_raises_with_detail(self):
        c = FakeClient({("GET", "c1"): {"status_code": "ERROR", "status": "Bad video"}})
        with self.assertRaises(MediaProcessingError) as cm:
            publisher.wait_until_ready(c, "c1")
        self.assertIn("Bad video", str(cm.exception))
        self.assertIn("c1", str(cm.exception))

    def test_expired_without_detail_uses_status_code(self):
        c = FakeClient({("GET", "c1"): {"status_code": "EXPIRED"}})
        with self.assertRaises(MediaProcessingError) as cm:
            publisher.wait_until_ready(c, "c1")
        self.assertIn("EXPIRED", str(cm.exception))

    def test_times_out(self):
        c = FakeClient({("GET", "c1"): {"status_code": "IN_PROGRESS"}})
        with self.assertRaises(MediaTimeoutError) as cm:
            publisher.wait_until_ready(c, "c1", timeout=20, interval=5)
        self.assertIn("20 seconds", str(cm.exception))
        self.assertEqual(self.clock.sleeps, [5, 5, 5, 5])

    def test_missing_status_code_keeps_polling(self):
        c = FakeClient({("GET", "c1"): [{}, {"status_code": "FINISHED"}]})
        publisher.wait_until_ready(c, "c1", interval=1)
        self.assertEqual(self.clock.sleeps, [1])

    def test_api_error_propagates(self):
        c = FakeClient({("GET", "c1"): GraphAPIError(500, "down")})
        with self.assertRaises(GraphAPIError):
            publisher.wait_until_ready(c, "c1")


class PublishTests(unittest.TestCase):
    def test_publish_container(self):
        c = FakeClient({("POST", "1784/media_publish"): {"id": "m1"}})
        self.assertEqual(publisher.publish_container(c, "c1"), {"id": "m1"})
        self.assertEqual(c.calls[0][2], {"creation_id": "c1"})

    def test_publish_media_full_flow_order(self):
        c = FakeClient(
            {
                ("POST", "1784/media"): {"id": "c1"},
                ("GET", "c1"): {"status_code": "FINISHED"},
                ("POST", "1784/media_publish"): {"id": "m1"},
            }
        )
        result = publisher.publish_media(c, image_url="u", caption="x")
        self.assertEqual(result, {"id": "m1"})
        self.assertEqual(
            [(m, p) for m, p, _ in c.calls],
            [("POST", "1784/media"), ("GET", "c1"), ("POST", "1784/media_publish")],
        )

    def test_publish_media_does_not_publish_when_processing_fails(self):
        c = FakeClient(
            {
                ("POST", "1784/media"): {"id": "c1"},
                ("GET", "c1"): {"status_code": "ERROR", "status": "x"},
            }
        )
        with self.assertRaises(MediaProcessingError):
            publisher.publish_media(c, image_url="u")
        self.assertEqual(c.calls_for("POST", "1784/media_publish"), [])

    def test_publish_media_forwards_timeout_and_interval(self):
        c = FakeClient({("POST", "1784/media"): {"id": "c1"}})
        with mock.patch.object(publisher, "wait_until_ready") as wait, \
             mock.patch.object(publisher, "publish_container", return_value={"id": "m"}):
            publisher.publish_media(c, timeout=11, interval=2, image_url="u")
        wait.assert_called_once_with(c, "c1", timeout=11, interval=2)


if __name__ == "__main__":
    unittest.main()
