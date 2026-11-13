import unittest

from instagram.resources import hashtag
from instagram.tests.helpers import FakeClient


def page(n, start=0, after=None, has_next=False):
    out = {"data": [{"id": str(start + i)} for i in range(n)]}
    if after is not None:
        out["paging"] = {"cursors": {"after": after}}
        if has_next:
            out["paging"]["next"] = "https://next"
    return out


class CleanNameTests(unittest.TestCase):
    def test_strips_hash_and_whitespace(self):
        self.assertEqual(hashtag._clean_name(" #travel "), "travel")
        self.assertEqual(hashtag._clean_name("##a"), "a")

    def test_invalid(self):
        for bad in ("", None, "#", "  ", "two words", "a\tb"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                hashtag._clean_name(bad)


class SearchTests(unittest.TestCase):
    def test_search_sends_user_id_and_query(self):
        c = FakeClient({("GET", "ig_hashtag_search"): {"data": [{"id": "h1"}]}})
        self.assertEqual(hashtag.search_hashtag(c, "#cats"), {"data": [{"id": "h1"}]})
        self.assertEqual(c.calls[0][2], {"user_id": "1784", "q": "cats"})

    def test_get_hashtag_id(self):
        c = FakeClient({("GET", "ig_hashtag_search"): {"data": [{"id": "h1"}, {"id": "h2"}]}})
        self.assertEqual(hashtag.get_hashtag_id(c, "cats"), "h1")

    def test_get_hashtag_id_not_found(self):
        c = FakeClient({("GET", "ig_hashtag_search"): {"data": []}})
        with self.assertRaises(LookupError):
            hashtag.get_hashtag_id(c, "nothing")
        c = FakeClient({("GET", "ig_hashtag_search"): {}})
        with self.assertRaises(LookupError):
            hashtag.get_hashtag_id(c, "nothing")


class MediaTests(unittest.TestCase):
    def test_recent_media_single_page(self):
        c = FakeClient({("GET", "h1/recent_media"): page(3)})
        items = hashtag.get_recent_media(c, "h1", limit=3)
        self.assertEqual(len(items), 3)
        self.assertEqual(
            c.calls[0][2],
            {"user_id": "1784", "fields": hashtag.DEFAULT_MEDIA_FIELDS, "limit": 3, "after": None},
        )

    def test_top_media_uses_top_edge(self):
        c = FakeClient({("GET", "h1/top_media"): page(1)})
        self.assertEqual(len(hashtag.get_top_media(c, "h1", limit=1)), 1)

    def test_limit_truncates_results(self):
        c = FakeClient({("GET", "h1/recent_media"): page(10, after="A", has_next=True)})
        items = hashtag.get_recent_media(c, "h1", limit=4)
        self.assertEqual([i["id"] for i in items], ["0", "1", "2", "3"])
        self.assertEqual(len(c.calls), 1)

    def test_page_size_is_capped_at_50(self):
        c = FakeClient({("GET", "h1/recent_media"): page(1)})
        hashtag.get_recent_media(c, "h1", limit=500)
        self.assertEqual(c.calls[0][2]["limit"], hashtag.MAX_PAGE_SIZE)

    def test_limit_across_pages(self):
        c = FakeClient(
            {("GET", "h1/recent_media"): [page(50, 0, "A", True), page(50, 50, "B", True)]}
        )
        items = hashtag.get_recent_media(c, "h1", limit=70)
        self.assertEqual(len(items), 70)
        self.assertEqual(len(c.calls), 2)
        self.assertEqual(c.calls[1][2]["after"], "A")

    def test_return_all_follows_pages_until_exhausted(self):
        c = FakeClient(
            {("GET", "h1/top_media"): [page(2, 0, "A", True), page(2, 2, "B", True), page(1, 4)]}
        )
        items = hashtag.get_top_media(c, "h1", return_all=True)
        self.assertEqual(len(items), 5)
        self.assertEqual(len(c.calls), 3)

    def test_return_all_respects_max_items(self):
        c = FakeClient({("GET", "h1/top_media"): page(50, 0, "A", True)})
        items = hashtag.get_top_media(c, "h1", return_all=True, max_items=30)
        self.assertEqual(len(items), 30)
        self.assertEqual(c.calls[0][2]["limit"], 30)

    def test_return_all_default_ceiling(self):
        self.assertEqual(hashtag.DEFAULT_MAX_ITEMS, 500)
        c = FakeClient({("GET", "h1/recent_media"): lambda **p: page(50, 0, "A", True)})
        items = hashtag.get_recent_media(c, "h1", return_all=True)
        self.assertEqual(len(items), 500)
        self.assertEqual(len(c.calls), 10)

    def test_stops_when_no_cursor_or_next(self):
        c = FakeClient({("GET", "h1/recent_media"): page(2)})
        self.assertEqual(len(hashtag.get_recent_media(c, "h1", limit=50)), 2)
        self.assertEqual(len(c.calls), 1)

    def test_resolves_hashtag_name_when_id_missing(self):
        c = FakeClient(
            {
                ("GET", "ig_hashtag_search"): {"data": [{"id": "h9"}]},
                ("GET", "h9/recent_media"): page(1),
            }
        )
        items = hashtag.get_recent_media(c, hashtag_name="#cats", limit=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(c.calls[0][1], "ig_hashtag_search")

    def test_hashtag_id_skips_search(self):
        c = FakeClient({("GET", "h1/recent_media"): page(1)})
        hashtag.get_recent_media(c, "h1", hashtag_name="ignored", limit=1)
        self.assertEqual(c.calls_for("GET", "ig_hashtag_search"), [])

    def test_missing_id_and_name(self):
        with self.assertRaises(ValueError):
            hashtag.get_recent_media(FakeClient())

    def test_invalid_limit(self):
        c = FakeClient({("GET", "h1/recent_media"): page(1)})
        with self.assertRaises(ValueError):
            hashtag.get_recent_media(c, "h1", limit=0)
        self.assertEqual(c.calls, [])

    def test_invalid_max_items_only_checked_with_return_all(self):
        c = FakeClient({("GET", "h1/recent_media"): page(1)})
        with self.assertRaises(ValueError):
            hashtag.get_recent_media(c, "h1", return_all=True, max_items=0)
        hashtag.get_recent_media(c, "h1", limit=1, max_items=0)  # ignored without return_all

    def test_custom_fields(self):
        c = FakeClient({("GET", "h1/top_media"): page(1)})
        hashtag.get_top_media(c, "h1", limit=1, fields="id")
        self.assertEqual(c.calls[0][2]["fields"], "id")


if __name__ == "__main__":
    unittest.main()
