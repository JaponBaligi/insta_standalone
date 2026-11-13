import unittest

from instagram import exceptions as ex


class ExceptionTests(unittest.TestCase):
    def test_all_errors_inherit_from_instagram_error(self):
        for cls in (
            ex.ConfigError,
            ex.GraphAPIError,
            ex.MediaProcessingError,
            ex.MediaTimeoutError,
            ex.CarouselItemError,
        ):
            self.assertTrue(issubclass(cls, ex.InstagramError), cls)

    def test_graph_api_error_attributes_and_message(self):
        err = ex.GraphAPIError(400, "Bad", code=100, subcode=33, fbtrace_id="abc")
        self.assertEqual(err.status_code, 400)
        self.assertEqual(err.message, "Bad")
        self.assertEqual(err.code, 100)
        self.assertEqual(err.subcode, 33)
        self.assertEqual(err.fbtrace_id, "abc")
        self.assertEqual(str(err), "[400] Bad (code=100, subcode=33)")

    def test_graph_api_error_optional_fields_default_to_none(self):
        err = ex.GraphAPIError(500, "oops")
        self.assertIsNone(err.code)
        self.assertIsNone(err.subcode)
        self.assertIsNone(err.fbtrace_id)

    def test_carousel_item_error(self):
        cause = RuntimeError("boom")
        err = ex.CarouselItemError(3, "video", cause)
        self.assertEqual(err.index, 3)
        self.assertEqual(err.media_type, "video")
        self.assertEqual(str(err), "Carousel item 3 (video) failed: boom")


if __name__ == "__main__":
    unittest.main()
