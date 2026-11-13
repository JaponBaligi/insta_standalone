import json
import logging
import unittest

from instagram.exceptions import CarouselItemError, MediaProcessingError
from instagram.resources import carousel
from instagram.tests.helpers import FakeClient

IMG1 = "https://x/1.jpg"
IMG2 = "https://x/2.png"
VID = "https://x/v.mp4"


class DetectMediaTypeTests(unittest.TestCase):
    def test_images(self):
        for url in (IMG1, "https://x/a.png", "https://x/noext", "https://x/a.jpg?file=b.mp4"):
            self.assertEqual(carousel.detect_media_type(url), "image", url)

    def test_videos_case_insensitive_and_query_safe(self):
        for url in (VID, "https://x/V.MOV", "https://x/c.webm?sig=1&x=2", "https://x/d.3gp"):
            self.assertEqual(carousel.detect_media_type(url), "video", url)


class NormalizeItemsTests(unittest.TestCase):
    def test_strings_auto_detect(self):
        self.assertEqual(
            carousel.normalize_items([IMG1, f" {VID} "]),
            [{"media_type": "image", "url": IMG1}, {"media_type": "video", "url": VID}],
        )

    def test_global_media_type_override(self):
        out = carousel.normalize_items([IMG1, IMG2], media_type="video")
        self.assertEqual([i["media_type"] for i in out], ["video", "video"])

    def test_dict_items_with_alternate_url_keys(self):
        out = carousel.normalize_items(
            [{"url": IMG1}, {"image_url": IMG2}, {"video_url": VID}]
        )
        self.assertEqual([i["url"] for i in out], [IMG1, IMG2, VID])
        self.assertEqual(out[2]["media_type"], "video")

    def test_dict_media_type_overrides_and_is_lowercased(self):
        out = carousel.normalize_items([{"url": IMG1, "media_type": "VIDEO"}, IMG2])
        self.assertEqual(out[0]["media_type"], "video")

    def test_user_tags_are_kept(self):
        tags = [{"username": "a"}]
        out = carousel.normalize_items([{"url": IMG1, "user_tags": tags}, IMG2])
        self.assertEqual(out[0]["user_tags"], tags)
        self.assertNotIn("user_tags", out[1])

    def test_invalid_global_media_type(self):
        with self.assertRaises(ValueError):
            carousel.normalize_items([IMG1, IMG2], media_type="gif")

    def test_invalid_item_media_type(self):
        with self.assertRaises(ValueError):
            carousel.normalize_items([{"url": IMG1, "media_type": "gif"}, IMG2])

    def test_empty_url(self):
        for bad in ("", "  ", {"url": ""}, {}):
            with self.assertRaises(ValueError, msg=bad):
                carousel.normalize_items([bad, IMG2])

    def test_wrong_item_type(self):
        with self.assertRaises(ValueError):
            carousel.normalize_items([123, IMG2])

    def test_invalid_url_is_rejected_with_position(self):
        for bad in ("ftp://x/a.jpg", "x/a.jpg", "https://", "javascript:alert(1)"):
            with self.assertRaises(ValueError, msg=bad) as cm:
                carousel.normalize_items([IMG1, bad])
            self.assertIn("2", str(cm.exception))

    def test_item_count_bounds(self):
        with self.assertRaises(ValueError):
            carousel.normalize_items([IMG1])
        with self.assertRaises(ValueError):
            carousel.normalize_items([IMG1] * (carousel.MAX_ITEMS + 1))
        self.assertEqual(len(carousel.normalize_items([IMG1] * 2)), 2)
        self.assertEqual(len(carousel.normalize_items([IMG1] * 10)), 10)

    def test_accepts_generators(self):
        self.assertEqual(len(carousel.normalize_items(u for u in (IMG1, IMG2))), 2)


class ItemsFromFieldTests(unittest.TestCase):
    def test_reads_list_field(self):
        out = carousel.carousel_items_from_field({"urls": [IMG1, VID]}, "urls")
        self.assertEqual([i["media_type"] for i in out], ["image", "video"])

    def test_field_name_required(self):
        with self.assertRaises(ValueError):
            carousel.carousel_items_from_field({"urls": [IMG1, IMG2]}, "")

    def test_field_must_be_list(self):
        for data in ({}, {"urls": "https://x/a.jpg"}, {"urls": None}):
            with self.assertRaises(ValueError, msg=data):
                carousel.carousel_items_from_field(data, "urls")

    def test_tuple_is_accepted(self):
        self.assertEqual(len(carousel.carousel_items_from_field({"u": (IMG1, IMG2)}, "u")), 2)


class BuildChildParamsTests(unittest.TestCase):
    def test_image_child(self):
        p = carousel.build_child_params({"media_type": "image", "url": IMG1})
        self.assertEqual(p, {"image_url": IMG1, "is_carousel_item": "true"})

    def test_image_child_with_user_tags(self):
        p = carousel.build_child_params(
            {"media_type": "image", "url": IMG1, "user_tags": [{"username": "a"}]}
        )
        self.assertEqual(json.loads(p["user_tags"])[0]["username"], "a")

    def test_video_child(self):
        p = carousel.build_child_params({"media_type": "video", "url": VID})
        self.assertEqual(
            p, {"media_type": "VIDEO", "video_url": VID, "is_carousel_item": True}
        )

    def test_video_child_user_tags_warns_and_is_skipped(self):
        with self.assertLogs(carousel.log, level=logging.WARNING):
            p = carousel.build_child_params(
                {"media_type": "video", "url": VID, "user_tags": [{"username": "a"}]}
            )
        self.assertNotIn("user_tags", p)


class BuildParentParamsTests(unittest.TestCase):
    def test_minimal(self):
        self.assertEqual(
            carousel.build_parent_params(["a", "b"]),
            {"media_type": "CAROUSEL", "children": "a,b"},
        )

    def test_with_options(self):
        p = carousel.build_parent_params(
            ["a", "b"],
            "cap",
            collaborators="@x,y",
            location_id=9,
            product_tags=[{"product_id": "1"}],
        )
        self.assertEqual(p["caption"], "cap")
        self.assertEqual(p["location_id"], "9")
        self.assertEqual(json.loads(p["collaborators"]), ["x", "y"])
        self.assertEqual(json.loads(p["product_tags"])[0]["product_id"], "1")


def publish_routes(children=("c1", "c2"), parent="p1", statuses=None):
    statuses = statuses or {}
    routes = {
        ("POST", "1784/media"): [{"id": i} for i in (*children, parent)],
        ("POST", "1784/media_publish"): {"id": "m1"},
    }
    for cid in (*children, parent):
        routes[("GET", cid)] = statuses.get(cid, {"status_code": "FINISHED"})
    return routes


class PublishCarouselTests(unittest.TestCase):
    def test_full_flow(self):
        c = FakeClient(publish_routes())
        result = carousel.publish_carousel(c, [IMG1, VID], "cap", interval=0)
        self.assertEqual(result, {"id": "m1"})

        media_calls = c.calls_for("POST", "1784/media")
        self.assertEqual(len(media_calls), 3)
        self.assertEqual(media_calls[0]["image_url"], IMG1)
        self.assertEqual(media_calls[1]["video_url"], VID)
        self.assertEqual(media_calls[2]["media_type"], "CAROUSEL")
        self.assertEqual(media_calls[2]["children"], "c1,c2")
        self.assertEqual(media_calls[2]["caption"], "cap")
        self.assertEqual(c.calls_for("POST", "1784/media_publish")[0], {"creation_id": "p1"})

    def test_children_are_awaited_before_parent_creation(self):
        c = FakeClient(publish_routes())
        carousel.publish_carousel(c, [IMG1, IMG2], interval=0)
        order = [(m, p) for m, p, _ in c.calls]
        self.assertEqual(
            order,
            [
                ("POST", "1784/media"), ("GET", "c1"),
                ("POST", "1784/media"), ("GET", "c2"),
                ("POST", "1784/media"), ("GET", "p1"),
                ("POST", "1784/media_publish"),
            ],
        )

    def test_caption_too_long_fails_before_api_calls(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            carousel.publish_carousel(c, [IMG1, IMG2], "x" * (carousel.CAPTION_MAX + 1))
        self.assertEqual(c.calls, [])

    def test_invalid_url_fails_before_api_calls(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            carousel.publish_carousel(c, [IMG1, "not-a-url"])
        self.assertEqual(c.calls, [])

    def test_child_processing_failure_wraps_error_with_position(self):
        c = FakeClient(
            publish_routes(statuses={"c2": {"status_code": "ERROR", "status": "bad video"}})
        )
        with self.assertRaises(CarouselItemError) as cm:
            carousel.publish_carousel(c, [IMG1, VID], interval=0)
        err = cm.exception
        self.assertEqual((err.index, err.media_type), (2, "video"))
        self.assertIsInstance(err.__cause__, MediaProcessingError)
        self.assertIn("Carousel item 2 (video) failed", str(err))
        self.assertEqual(c.calls_for("POST", "1784/media_publish"), [])

    def test_child_creation_failure_is_wrapped(self):
        boom = RuntimeError("create failed")
        c = FakeClient({("POST", "1784/media"): [boom]})
        with self.assertRaises(CarouselItemError) as cm:
            carousel.publish_carousel(c, [IMG1, IMG2], interval=0)
        self.assertEqual(cm.exception.index, 1)
        self.assertIs(cm.exception.__cause__, boom)

    def test_parent_failure_is_not_wrapped(self):
        c = FakeClient(
            publish_routes(statuses={"p1": {"status_code": "ERROR", "status": "x"}})
        )
        with self.assertRaises(MediaProcessingError):
            carousel.publish_carousel(c, [IMG1, IMG2], interval=0)

    def test_default_timeout_constant(self):
        self.assertEqual(carousel.CAROUSEL_TIMEOUT, 900)
        self.assertEqual((carousel.MIN_ITEMS, carousel.MAX_ITEMS), (2, 10))


if __name__ == "__main__":
    unittest.main()
