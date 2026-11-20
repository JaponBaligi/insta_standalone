import unittest
from unittest import mock

from instagram.automation import jobs
from instagram.tests.helpers import FakeClient


class ParseJobTests(unittest.TestCase):
    def test_image_requires_url(self):
        with self.assertRaises(jobs.JobError):
            jobs.parse_job({"type": "image"})
        job = jobs.parse_job({"type": "image", "image_url": " https://x/a.jpg ", "caption": "hi"})
        self.assertEqual(job["type"], "image")
        self.assertEqual(job["image_url"], "https://x/a.jpg")
        self.assertEqual(job["caption"], "hi")

    def test_story_needs_exactly_one_source(self):
        with self.assertRaises(jobs.JobError):
            jobs.parse_job({"type": "story"})
        with self.assertRaises(jobs.JobError):
            jobs.parse_job(
                {"type": "story", "image_url": "https://a.jpg", "video_url": "https://b.mp4"}
            )
        self.assertEqual(
            jobs.parse_job({"type": "story", "image_url": "https://a.jpg"})["image_url"],
            "https://a.jpg",
        )

    def test_carousel_needs_items(self):
        with self.assertRaises(jobs.JobError):
            jobs.parse_job({"type": "carousel", "items": []})
        job = jobs.parse_job({"type": "carousel", "items": ["https://a.jpg", "https://b.jpg"]})
        self.assertEqual(len(job["items"]), 2)

    def test_unknown_type(self):
        with self.assertRaises(jobs.JobError):
            jobs.parse_job({"type": "podcast"})


class RunJobTests(unittest.TestCase):
    def test_dispatches_image(self):
        client = FakeClient()
        with mock.patch("instagram.automation.jobs.image.publish_image", return_value={"id": "1"}) as pub:
            out = jobs.run_job(client, {"type": "image", "image_url": "https://a.jpg", "caption": "c"})
        self.assertEqual(out, {"ok": True, "type": "image", "result": {"id": "1"}})
        pub.assert_called_once_with(client, "https://a.jpg", caption="c")

    def test_dispatches_reel_story_carousel(self):
        client = FakeClient()
        with mock.patch("instagram.automation.jobs.reel.publish_reel", return_value={"id": "r"}) as r:
            jobs.run_job(client, {"type": "reel", "video_url": "https://v.mp4", "caption": ""})
        r.assert_called_once()
        with mock.patch("instagram.automation.jobs.story.publish_story", return_value={"id": "s"}) as s:
            jobs.run_job(client, {"type": "story", "image_url": "https://a.jpg", "caption": ""})
        s.assert_called_once()
        with mock.patch(
            "instagram.automation.jobs.carousel.publish_carousel", return_value={"id": "c"}
        ) as c:
            jobs.run_job(
                client,
                {"type": "carousel", "items": ["https://a.jpg", "https://b.jpg"], "caption": "x"},
            )
        c.assert_called_once()


class BearerAuthTests(unittest.TestCase):
    def test_accepts_matching_bearer(self):
        from instagram.automation.auth import check_bearer

        self.assertTrue(check_bearer("Bearer secret", "secret"))
        self.assertFalse(check_bearer("Bearer nope", "secret"))
        self.assertFalse(check_bearer(None, "secret"))
        self.assertFalse(check_bearer("Bearer secret", ""))


if __name__ == "__main__":
    unittest.main()
