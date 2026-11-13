import json
import time
import unittest
from pathlib import Path

from instagram import token_store
from instagram.tests.helpers import IsolatedTokenStoreTestCase

REAL_STORE_PATH = token_store.STORE_PATH  # captured before any patching


class TokenStoreTests(IsolatedTokenStoreTestCase):
    def test_default_path_is_project_root_token_file(self):
        self.assertEqual(REAL_STORE_PATH.name, ".token.json")
        self.assertEqual(REAL_STORE_PATH.parent.name, "token")
        project_root = REAL_STORE_PATH.parent.parent
        self.assertTrue((project_root / "instagram").is_dir())

    def test_load_missing_returns_none(self):
        self.assertIsNone(token_store.load())

    def test_save_then_load_roundtrip(self):
        before = int(time.time())
        saved = token_store.save("abc", 3600)
        after = int(time.time())
        self.assertEqual(token_store.load(), saved)
        self.assertEqual(saved["access_token"], "abc")
        self.assertTrue(before + 3600 <= saved["expires_at"] <= after + 3600)
        self.assertTrue(before <= saved["saved_at"] <= after)

    def test_save_creates_parent_directory(self):
        self.assertFalse(self.store_path.parent.exists())
        token_store.save("abc")
        self.assertTrue(self.store_path.exists())

    def test_save_without_expiry_stores_none(self):
        for value in (None, 0):
            saved = token_store.save("abc", value)
            self.assertIsNone(saved["expires_at"])

    def test_expires_in_string_is_accepted(self):
        saved = token_store.save("abc", "100")
        self.assertAlmostEqual(saved["expires_at"], int(time.time()) + 100, delta=2)

    def test_save_overwrites_previous_token(self):
        token_store.save("old", 10)
        token_store.save("new", 10)
        self.assertEqual(token_store.load()["access_token"], "new")

    def test_load_corrupt_json_returns_none(self):
        self.store_path.parent.mkdir(parents=True)
        self.store_path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(token_store.load())

    def test_file_content_is_json(self):
        token_store.save("abc", 10)
        data = json.loads(Path(self.store_path).read_text(encoding="utf-8"))
        self.assertEqual(data["access_token"], "abc")


class SecondsLeftTests(unittest.TestCase):
    def test_none_and_empty(self):
        self.assertIsNone(token_store.seconds_left(None))
        self.assertIsNone(token_store.seconds_left({}))

    def test_no_expiry_info(self):
        self.assertIsNone(token_store.seconds_left({"expires_at": None}))

    def test_future_expiry(self):
        left = token_store.seconds_left({"expires_at": int(time.time()) + 500})
        self.assertTrue(497 <= left <= 500)

    def test_past_expiry_is_negative(self):
        self.assertLess(token_store.seconds_left({"expires_at": int(time.time()) - 10}), 0)


if __name__ == "__main__":
    unittest.main()
