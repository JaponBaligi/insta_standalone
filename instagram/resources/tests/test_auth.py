import unittest

from instagram import token_store
from instagram.exceptions import ConfigError
from instagram.resources import auth
from instagram.tests.helpers import FakeClient, IsolatedTokenStoreTestCase


class GetMeTests(unittest.TestCase):
    def test_get_me_default_and_custom_fields(self):
        c = FakeClient({("GET", "me"): {"id": "1"}})
        self.assertEqual(auth.get_me(c), {"id": "1"})
        auth.get_me(c, fields="id")
        self.assertEqual(c.calls[0][2], {"fields": "id,name"})
        self.assertEqual(c.calls[1][2], {"fields": "id"})


class ExchangeTests(unittest.TestCase):
    def test_requires_app_credentials(self):
        for app_id, secret in (("", ""), ("id", ""), ("", "sec")):
            c = FakeClient(app_id=app_id, app_secret=secret)
            with self.assertRaises(ConfigError, msg=(app_id, secret)):
                auth.exchange_access_token(c, "short")
        self.assertEqual(c.calls, [])

    def test_exchange_sends_expected_params(self):
        c = FakeClient(
            {("GET", "oauth/access_token"): {"access_token": "long"}},
            app_id="id",
            app_secret="sec",
        )
        self.assertEqual(auth.exchange_access_token(c, "short"), {"access_token": "long"})
        self.assertEqual(
            c.calls[0][2],
            {
                "grant_type": "fb_exchange_token",
                "client_id": "id",
                "client_secret": "sec",
                "fb_exchange_token": "short",
            },
        )

    def test_explicit_app_secret_overrides_config(self):
        c = FakeClient({("GET", "oauth/access_token"): {}}, app_id="id", app_secret="cfg")
        auth.exchange_access_token(c, "short", app_secret="explicit")
        self.assertEqual(c.calls[0][2]["client_secret"], "explicit")

    def test_explicit_secret_works_without_config_secret(self):
        c = FakeClient({("GET", "oauth/access_token"): {}}, app_id="id", app_secret="")
        auth.exchange_access_token(c, "short", app_secret="explicit")
        self.assertEqual(len(c.calls), 1)


class RefreshTests(IsolatedTokenStoreTestCase):
    def test_refresh_updates_client_and_store(self):
        c = FakeClient(
            {("GET", "oauth/access_token"): {"access_token": "NEW", "expires_in": 5000}},
            app_id="id",
            app_secret="sec",
            token="OLD",
        )
        result = auth.refresh_access_token(c)
        self.assertEqual(result["access_token"], "NEW")
        self.assertEqual(c.token, "NEW")
        self.assertEqual(c.calls[0][2]["fb_exchange_token"], "OLD")
        stored = token_store.load()
        self.assertEqual(stored["access_token"], "NEW")
        self.assertIsNotNone(stored["expires_at"])

    def test_refresh_without_token_in_response_keeps_old_token(self):
        c = FakeClient(
            {("GET", "oauth/access_token"): {}}, app_id="id", app_secret="sec", token="OLD"
        )
        auth.refresh_access_token(c)
        self.assertEqual(c.token, "OLD")
        self.assertIsNone(token_store.load())

    def test_refresh_requires_credentials(self):
        with self.assertRaises(ConfigError):
            auth.refresh_access_token(FakeClient())


if __name__ == "__main__":
    unittest.main()
