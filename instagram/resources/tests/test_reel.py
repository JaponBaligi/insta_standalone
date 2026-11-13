import json
import logging
import unittest
from unittest import mock

from instagram.resources import reel
from instagram.tests.helpers import FakeClient


class BuildReelParamsTests(unittest.TestCase):
    def test_minimal_has_default_share_to_feed(self):
        p = reel.build_reel_params("https://x/v.mp4")
        self.assertEqual(
            p, {"media_type": "REELS", "video_url": "https://x/v.mp4", "share_to_feed": "true"}
        )

    def test_video_url_required(self):
        with self.assertRaises(ValueError):
            reel.build_reel_params("")

    def test_caption_limit(self):
        reel.build_reel_params("u", "x" * reel.CAPTION_MAX)
        with self.assertRaises(ValueError):
            reel.build_reel_params("u", "x" * (reel.CAPTION_MAX + 1))

    def test_user_tags_drop_position(self):
        p = reel.build_reel_params("u", user_tags=[{"username": "@bob", "x": 0.1, "y": 0.9}])
        self.assertEqual(json.loads(p["user_tags"]), [{"username": "bob"}])

    def test_user_tag_validation_still_applies(self):
        with self.assertRaises(ValueError):
            reel.build_reel_params("u", user_tags=[{"username": ""}])

    def test_all_options(self):
        with self.assertLogs(reel.log, level=logging.WARNING):  # cover_url + offset
            p = self._build_all()
        self._check_all(p)

    def _build_all(self):
        return reel.build_reel_params(
            "u",
            "cap",
            audio_name="song",
            collaborators="@a,b",
            cover_url="https://c",
            location_id=7,
            product_tags=[{"product_id": "1"}],
            share_to_feed=False,
            thumbnail_offset=2,
            trial_graduation_strategy="MANUAL",
        )

    def _check_all(self, p):
        self.assertEqual(p["caption"], "cap")
        self.assertEqual(p["audio_name"], "song")
        self.assertEqual(json.loads(p["collaborators"]), ["a", "b"])
        self.assertEqual(p["cover_url"], "https://c")
        self.assertEqual(p["location_id"], "7")
        self.assertEqual(json.loads(p["product_tags"])[0]["product_id"], "1")
        self.assertEqual(p["share_to_feed"], "false")
        self.assertEqual(p["thumb_offset"], 2000)
        self.assertEqual(json.loads(p["trial_params"]), {"graduation_strategy": "MANUAL"})

    def test_share_to_feed_none_is_omitted(self):
        self.assertNotIn("share_to_feed", reel.build_reel_params("u", share_to_feed=None))

    def test_alt_text_is_dropped_with_warning(self):
        with self.assertLogs(reel.log, level=logging.WARNING):
            p = reel.build_reel_params("u", alt_text="alt")
        self.assertNotIn("alt_text", p)

    def test_cover_and_thumbnail_offset_warn(self):
        with self.assertLogs(reel.log, level=logging.WARNING) as logs:
            reel.build_reel_params("u", cover_url="https://c", thumbnail_offset=1)
        self.assertIn("cover_url", logs.output[0])

    def test_invalid_trial_strategy(self):
        with self.assertRaises(ValueError):
            reel.build_reel_params("u", trial_graduation_strategy="x")


class PublishReelTests(unittest.TestCase):
    def test_end_to_end(self):
        c = FakeClient(
            {
                ("POST", "1784/media"): {"id": "c1"},
                ("GET", "c1"): {"status_code": "FINISHED"},
                ("POST", "1784/media_publish"): {"id": "m1"},
            }
        )
        self.assertEqual(reel.publish_reel(c, "https://x/v.mp4", "hi", interval=0), {"id": "m1"})
        sent = c.calls_for("POST", "1784/media")[0]
        self.assertEqual(sent["media_type"], "REELS")
        self.assertEqual(sent["caption"], "hi")

    def test_uses_long_default_timeout(self):
        with mock.patch.object(reel, "publish_media", return_value={}) as pm:
            reel.publish_reel(FakeClient(), "u")
        self.assertEqual(pm.call_args[1]["timeout"], reel.REEL_TIMEOUT)
        self.assertEqual(reel.REEL_TIMEOUT, 900)

    def test_invalid_input_makes_no_api_call(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            reel.publish_reel(c, "")
        self.assertEqual(c.calls, [])


if __name__ == "__main__":
    unittest.main()
