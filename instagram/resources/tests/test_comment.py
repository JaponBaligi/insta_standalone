import unittest

from instagram.resources import comment
from instagram.tests.helpers import FakeClient


def page(ids, after=None, has_next=False):
    out = {"data": [{"id": i} for i in ids]}
    if after is not None:
        out["paging"] = {"cursors": {"after": after}}
        if has_next:
            out["paging"]["next"] = "https://next"
    return out


class RequireTests(unittest.TestCase):
    def test_strips_and_returns(self):
        self.assertEqual(comment._require("x", " 1 "), "1")

    def test_blank_and_none_raise(self):
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError, msg=bad):
                comment._require("media_id", bad)


class ListCommentsTests(unittest.TestCase):
    def test_single_page_params(self):
        c = FakeClient({("GET", "m1/comments"): page(["1"])})
        self.assertEqual(comment.list_comments(c, "m1", limit=10, after="A"), page(["1"]))
        self.assertEqual(
            c.calls[0][2], {"fields": comment.DEFAULT_FIELDS, "limit": 10, "after": "A"}
        )

    def test_media_id_required(self):
        with self.assertRaises(ValueError):
            comment.list_comments(FakeClient(), "")


class IterCommentsTests(unittest.TestCase):
    def test_follows_pagination(self):
        c = FakeClient(
            {("GET", "m1/comments"): [page(["1", "2"], "A", True), page(["3"], "B", False)]}
        )
        ids = [x["id"] for x in comment.iter_comments(c, "m1", page_size=2)]
        self.assertEqual(ids, ["1", "2", "3"])
        self.assertEqual([p["after"] for p in (cc[2] for cc in c.calls)], [None, "A"])
        self.assertEqual(c.calls[0][2]["limit"], 2)

    def test_stops_without_next_link(self):
        c = FakeClient({("GET", "m1/comments"): page(["1"], "A", has_next=False)})
        self.assertEqual(len(list(comment.iter_comments(c, "m1"))), 1)
        self.assertEqual(len(c.calls), 1)

    def test_stops_without_cursor(self):
        c = FakeClient({("GET", "m1/comments"): {"data": [{"id": "1"}], "paging": {"next": "x"}}})
        self.assertEqual(len(list(comment.iter_comments(c, "m1"))), 1)

    def test_empty_response(self):
        c = FakeClient({("GET", "m1/comments"): {}})
        self.assertEqual(list(comment.iter_comments(c, "m1")), [])

    def test_max_items_stops_early_without_extra_requests(self):
        c = FakeClient(
            {("GET", "m1/comments"): [page(["1", "2", "3"], "A", True), page(["4"], "B")]}
        )
        ids = [x["id"] for x in comment.iter_comments(c, "m1", max_items=2)]
        self.assertEqual(ids, ["1", "2"])
        self.assertEqual(len(c.calls), 1)

    def test_list_all_comments(self):
        c = FakeClient(
            {("GET", "m1/comments"): [page(["1"], "A", True), page(["2"])]}
        )
        self.assertEqual([x["id"] for x in comment.list_all_comments(c, "m1")], ["1", "2"])

    def test_list_all_forwards_kwargs(self):
        c = FakeClient({("GET", "m1/comments"): page(["1"])})
        comment.list_all_comments(c, "m1", fields="id", page_size=7)
        self.assertEqual(c.calls[0][2]["fields"], "id")
        self.assertEqual(c.calls[0][2]["limit"], 7)


class ModerationTests(unittest.TestCase):
    def test_delete_uses_delete_verb(self):
        c = FakeClient({("DELETE", "c1"): {"success": True}})
        self.assertEqual(comment.delete_comment(c, "c1"), {"success": True})

    def test_hide_and_unhide(self):
        c = FakeClient({("POST", "c1"): {"success": True}})
        comment.hide_comment(c, "c1")
        comment.unhide_comment(c, "c1")
        self.assertEqual(c.calls[0][2], {"hide": True})
        self.assertEqual(c.calls[1][2], {"hide": False})

    def test_disable_and_enable_comments(self):
        c = FakeClient({("POST", "m1"): {"success": True}})
        comment.disable_comments(c, "m1")
        comment.enable_comments(c, "m1")
        self.assertEqual(c.calls[0][2], {"comment_enabled": False})
        self.assertEqual(c.calls[1][2], {"comment_enabled": True})

    def test_ids_are_required(self):
        c = FakeClient()
        for fn in (comment.delete_comment, comment.hide_comment, comment.unhide_comment,
                   comment.disable_comments, comment.enable_comments):
            with self.assertRaises(ValueError, msg=fn.__name__):
                fn(c, " ")
        self.assertEqual(c.calls, [])


class PublicCommentTests(unittest.TestCase):
    def test_create_comment_on_media(self):
        c = FakeClient({("POST", "m1/comments"): {"id": "c9"}})
        self.assertEqual(comment.create_comment(c, " m1 ", " nice "), {"id": "c9"})
        self.assertEqual(c.calls[0][2], {"message": "nice"})

    def test_reply_to_comment(self):
        c = FakeClient({("POST", "c1/replies"): {"id": "c2"}})
        self.assertEqual(comment.reply_to_comment(c, "c1", "thanks"), {"id": "c2"})
        self.assertEqual(c.calls[0][2], {"message": "thanks"})

    def test_public_comment_validation(self):
        c = FakeClient()
        with self.assertRaises(ValueError):
            comment.create_comment(c, "", "hi")
        with self.assertRaises(ValueError):
            comment.reply_to_comment(c, "c1", "  ")
        self.assertEqual(c.calls, [])


if __name__ == "__main__":
    unittest.main()
