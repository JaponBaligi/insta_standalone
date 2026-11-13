import json
import logging
import unittest
from unittest import mock

from instagram.resources import story
from instagram.tests.helpers import FakeClient


class BuildStoryParamsTests(unittest.TestCase):
    def test_video_story(self):
        self.assertEqual(
            story.build_story_params("https://x/v.mp4"),
            {"media_type": "STORIES", "video_url": "https://x/v.mp4"},
        )

    def test_image_story(self):
        self.assertEqual(
            story.build_story_params(image_url="https://x/a.jpg"),
            {"media_type": "STORIES", "image_url": "https://x/a.jpg"},
        )

    def test_exactly_one_source_required(self):
        for kwargs in ({}, {"video_url": "v", "image_url": "i"}):
            with self.assertRaises(ValueError, msg=kwargs):
                story.build_story_params(**kwargs)

    def test_user_tags_only_username(self):
        p = story.build_story_params("v", user_tags=[{"username": "@bob", "x": 0.3}])
        self.assertEqual(json.loads(p["user_tags"]), [{"username": "bob"}])

    def test_unsupported_fields_warn_and_are_not_sent(self):
        with self.assertLogs(story.log, level=logging.WARNING) as logs:
            p = story.build_story_params(
                "v",
                "caption",
                alt_text="a",
                audio_name="s",
                collaborators="x",
                cover_url="c",
                location_id="1",
                product_tags=[{"product_id": "1"}],
                thumbnail_offset=1,
                trial_graduation_strategy="MANUAL",
                share_to_feed=False,
            )
        self.assertEqual(p, {"media_type": "STORIES", "video_url": "v"})
        for name in ("caption", "alt_text", "audio_name", "collaborators", "cover_url",
                     "location_id", "product_tags", "thumbnail_offset",
                     "trial_graduation_strategy", "share_to_feed"):
            self.assertIn(name, logs.output[0])

    def test_default_share_to_feed_true_does_not_warn(self):
        with self.assertNoLogs(story.log, level=logging.WARNING):
            story.build_story_params("v")

    def test_invalid_trial_strategy(self):
        with self.assertRaises(ValueError):
            story.build_story_params("v", trial_graduation_strategy="bad")


class PublishStoryTests(unittest.TestCase):
    def test_video_end_to_end(self):
        c = FakeClient(
            {
                ("POST", "1784/media"): {"id": "c1"},
                ("GET", "c1"): {"status_code": "FINISHED"},
                ("POST", "1784/media_publish"): {"id": "m1"},
            }
        )
        self.assertEqual(story.publish_story(c, "https://x/v.mp4", interval=0), {"id": "m1"})
        self.assertEqual(c.calls_for("POST", "1784/media")[0]["media_type"], "STORIES")

    def test_image_story(self):
        with mock.patch.object(story, "publish_media", return_value={"id": "m"}) as pm:
            story.publish_story(FakeClient(), image_url="https://x/a.jpg")
        self.assertEqual(pm.call_args[1]["image_url"], "https://x/a.jpg")
        self.assertNotIn("video_url", pm.call_args[1])

    def test_default_timeout(self):
        with mock.patch.object(story, "publish_media", return_value={}) as pm:
            story.publish_story(FakeClient(), "v")
        self.assertEqual(pm.call_args[1]["timeout"], story.STORY_TIMEOUT)

    def test_invalid_input_makes_no_api_call(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            story.publish_story(c)
        self.assertEqual(c.calls, [])


if __name__ == "__main__":
    unittest.main()
