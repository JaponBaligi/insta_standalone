import json
import logging
import unittest
from unittest import mock

from instagram.resources import image
from instagram.tests.helpers import FakeClient


class CsvOrListTests(unittest.TestCase):
    def test_empty_values(self):
        self.assertEqual(image._csv_or_list(None), [])
        self.assertEqual(image._csv_or_list(""), [])
        self.assertEqual(image._csv_or_list([]), [])

    def test_csv_string_strips_and_removes_at_sign(self):
        self.assertEqual(image._csv_or_list(" @a, b ,, @c "), ["a", "b", "c"])

    def test_iterable(self):
        self.assertEqual(image._csv_or_list(["@x", " y ", ""]), ["x", "y"])
        self.assertEqual(image._csv_or_list(("a",)), ["a"])


class CheckPosTests(unittest.TestCase):
    def test_bounds_are_inclusive(self):
        self.assertEqual(image._check_pos("x", 0), 0.0)
        self.assertEqual(image._check_pos("x", 1), 1.0)
        self.assertEqual(image._check_pos("x", "0.25"), 0.25)

    def test_out_of_range(self):
        for bad in (-0.01, 1.01, 5):
            with self.assertRaises(ValueError, msg=bad):
                image._check_pos("x", bad)


class UserTagTests(unittest.TestCase):
    def test_none_and_empty(self):
        self.assertEqual(image.build_user_tags(None), [])
        self.assertEqual(image.build_user_tags([]), [])

    def test_defaults_center_and_strips_at(self):
        self.assertEqual(
            image.build_user_tags([{"username": " @bob "}]),
            [{"username": "bob", "x": 0.5, "y": 0.5}],
        )

    def test_explicit_position(self):
        out = image.build_user_tags([{"username": "a", "x": 0, "y": 1}])
        self.assertEqual(out, [{"username": "a", "x": 0.0, "y": 1.0}])

    def test_empty_username_rejected(self):
        for tag in ({}, {"username": ""}, {"username": " @ "}):
            with self.assertRaises(ValueError, msg=tag):
                image.build_user_tags([tag])

    def test_bad_position_rejected(self):
        with self.assertRaises(ValueError):
            image.build_user_tags([{"username": "a", "x": 2}])


class ProductTagTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(
            image.build_product_tags([{"product_id": 123, "y": 0.1}]),
            [{"product_id": "123", "x": 0.5, "y": 0.1}],
        )

    def test_none(self):
        self.assertEqual(image.build_product_tags(None), [])

    def test_missing_product_id(self):
        with self.assertRaises(ValueError):
            image.build_product_tags([{"product_id": " "}])

    def test_bad_position(self):
        with self.assertRaises(ValueError):
            image.build_product_tags([{"product_id": "1", "x": -1}])


class BuildImageParamsTests(unittest.TestCase):
    def test_minimal(self):
        self.assertEqual(image.build_image_params("https://x/a.jpg"), {"image_url": "https://x/a.jpg"})

    def test_empty_url_rejected(self):
        with self.assertRaises(ValueError):
            image.build_image_params("")

    def test_caption_included(self):
        self.assertEqual(image.build_image_params("u", "hello")["caption"], "hello")

    def test_caption_limit(self):
        image.build_image_params("u", "x" * image.CAPTION_MAX)
        with self.assertRaises(ValueError):
            image.build_image_params("u", "x" * (image.CAPTION_MAX + 1))

    def test_carousel_item_drops_caption_and_sets_flag(self):
        p = image.build_image_params("u", "ignored", is_carousel_item=True)
        self.assertEqual(p, {"image_url": "u", "is_carousel_item": "true"})

    def test_optional_fields(self):
        p = image.build_image_params(
            "u",
            "c",
            alt_text="alt",
            location_id=55,
            collaborators="@a, b",
            user_tags=[{"username": "bob", "x": 0.1, "y": 0.2}],
            product_tags=[{"product_id": "9"}],
        )
        self.assertEqual(p["alt_text"], "alt")
        self.assertEqual(p["location_id"], "55")
        self.assertEqual(json.loads(p["collaborators"]), ["a", "b"])
        self.assertEqual(json.loads(p["user_tags"]), [{"username": "bob", "x": 0.1, "y": 0.2}])
        self.assertEqual(json.loads(p["product_tags"]), [{"product_id": "9", "x": 0.5, "y": 0.5}])

    def test_reel_only_fields_are_ignored_with_warning(self):
        with self.assertLogs(image.log, level=logging.WARNING) as logs:
            p = image.build_image_params(
                "u",
                audio_name="a",
                cover_url="c",
                thumbnail_offset=1.5,
                trial_graduation_strategy="MANUAL",
                share_to_feed=False,
            )
        self.assertEqual(p, {"image_url": "u"})
        message = logs.output[0]
        for name in ("audio_name", "cover_url", "thumbnail_offset",
                     "trial_graduation_strategy", "share_to_feed"):
            self.assertIn(name, message)

    def test_share_to_feed_true_or_none_does_not_warn(self):
        with self.assertNoLogs(image.log, level=logging.WARNING):
            image.build_image_params("u", share_to_feed=True)
            image.build_image_params("u", share_to_feed=None)

    def test_invalid_trial_strategy(self):
        with self.assertRaises(ValueError):
            image.build_image_params("u", trial_graduation_strategy="NOPE")


class BuildReelExtrasTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(image.build_reel_extras(), {})

    def test_all_fields(self):
        extras = image.build_reel_extras(
            audio_name="song",
            cover_url="https://c",
            share_to_feed=False,
            thumbnail_offset=1.5,
            trial_graduation_strategy="SS_PERFORMANCE",
        )
        self.assertEqual(extras["audio_name"], "song")
        self.assertEqual(extras["cover_url"], "https://c")
        self.assertEqual(extras["share_to_feed"], "false")
        self.assertEqual(extras["thumb_offset"], 1500)
        self.assertEqual(json.loads(extras["trial_params"]),
                         {"graduation_strategy": "SS_PERFORMANCE"})

    def test_share_to_feed_true(self):
        self.assertEqual(image.build_reel_extras(share_to_feed=True), {"share_to_feed": "true"})

    def test_zero_thumbnail_offset_is_omitted(self):
        self.assertNotIn("thumb_offset", image.build_reel_extras(thumbnail_offset=0))

    def test_invalid_trial_strategy(self):
        with self.assertRaises(ValueError):
            image.build_reel_extras(trial_graduation_strategy="bad")


class PublishImageTests(unittest.TestCase):
    def test_end_to_end(self):
        c = FakeClient(
            {
                ("POST", "1784/media"): {"id": "c1"},
                ("GET", "c1"): {"status_code": "FINISHED"},
                ("POST", "1784/media_publish"): {"id": "m1"},
            }
        )
        result = image.publish_image(c, "https://x/a.jpg", "cap", interval=0)
        self.assertEqual(result, {"id": "m1"})
        self.assertEqual(
            c.calls_for("POST", "1784/media")[0],
            {"image_url": "https://x/a.jpg", "caption": "cap"},
        )
        self.assertEqual(c.calls_for("POST", "1784/media_publish")[0], {"creation_id": "c1"})

    def test_forwards_timeout_interval_and_fields(self):
        with mock.patch.object(image, "publish_media", return_value={"id": "m"}) as pm:
            image.publish_image(FakeClient(), "u", "c", timeout=9, interval=1, alt_text="a")
        _, kwargs = pm.call_args
        self.assertEqual(kwargs["timeout"], 9)
        self.assertEqual(kwargs["interval"], 1)
        self.assertEqual(kwargs["image_url"], "u")
        self.assertEqual(kwargs["alt_text"], "a")

    def test_validation_error_before_any_api_call(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            image.publish_image(c, "")
        self.assertEqual(c.calls, [])


if __name__ == "__main__":
    unittest.main()
