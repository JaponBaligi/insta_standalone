import unittest

from instagram.resources import page, user
from instagram.tests.helpers import FakeClient


class PageTests(unittest.TestCase):
    def test_list_pages(self):
        c = FakeClient({("GET", "me/accounts"): {"data": [{"id": "p1"}]}})
        self.assertEqual(page.list_pages(c), {"data": [{"id": "p1"}]})
        self.assertEqual(c.calls[0][2], {"fields": "id,name"})

    def test_list_pages_custom_fields(self):
        c = FakeClient({("GET", "me/accounts"): {}})
        page.list_pages(c, fields="id")
        self.assertEqual(c.calls[0][2], {"fields": "id"})

    def test_get_instagram_account(self):
        c = FakeClient({("GET", "p1"): {"instagram_business_account": {"id": "ig"}}})
        result = page.get_instagram_account(c, "p1")
        self.assertEqual(result["instagram_business_account"]["id"], "ig")
        self.assertEqual(
            c.calls[0][2], {"fields": "instagram_business_account{id,username,name}"}
        )


class UserTests(unittest.TestCase):
    def test_get_uses_configured_node(self):
        c = FakeClient({("GET", "1784"): {"id": "1784"}})
        self.assertEqual(user.get(c), {"id": "1784"})
        self.assertEqual(c.calls[0][2], {"fields": user.DEFAULT_USER_FIELDS})

    def test_get_custom_fields(self):
        c = FakeClient({("GET", "1784"): {}})
        user.get(c, fields="id")
        self.assertEqual(c.calls[0][2], {"fields": "id"})

    def test_get_media_defaults(self):
        c = FakeClient({("GET", "1784/media"): {"data": []}})
        user.get_media(c)
        self.assertEqual(
            c.calls[0][2],
            {"fields": user.DEFAULT_MEDIA_FIELDS, "limit": 25, "after": None},
        )

    def test_get_media_pagination_cursor(self):
        c = FakeClient({("GET", "1784/media"): {"data": []}})
        user.get_media(c, limit=5, after="CUR")
        self.assertEqual(c.calls[0][2]["limit"], 5)
        self.assertEqual(c.calls[0][2]["after"], "CUR")


if __name__ == "__main__":
    unittest.main()
