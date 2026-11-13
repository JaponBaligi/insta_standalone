import unittest

from instagram.resources import insights
from instagram.tests.helpers import FakeClient


class AccountInsightsTests(unittest.TestCase):
    def test_get_account_insights_params(self):
        c = FakeClient({("GET", "1784/insights"): {"data": [{"name": "reach"}]}})
        result = insights.get_account_insights(
            c, metrics=["reach", "views"], period="day", since=10, until=20
        )
        self.assertEqual(result["data"][0]["name"], "reach")
        self.assertEqual(
            c.calls[0][2],
            {"metric": "reach,views", "period": "day", "since": 10, "until": 20},
        )

    def test_metrics_string_accepted(self):
        c = FakeClient({("GET", "1784/insights"): {"data": []}})
        insights.get_account_insights(c, metrics="reach")
        self.assertEqual(c.calls[0][2]["metric"], "reach")

    def test_metrics_required(self):
        with self.assertRaises(ValueError):
            insights.get_account_insights(FakeClient(), metrics=[])


class MediaInsightsTests(unittest.TestCase):
    def test_get_media_insights(self):
        c = FakeClient({("GET", "m1/insights"): {"data": [{"name": "likes"}]}})
        result = insights.get_media_insights(c, " m1 ", metrics=["likes", "comments"])
        self.assertEqual(result["data"][0]["name"], "likes")
        self.assertEqual(c.calls[0][2], {"metric": "likes,comments"})

    def test_media_id_required(self):
        with self.assertRaises(ValueError):
            insights.get_media_insights(FakeClient(), "", metrics="reach")


if __name__ == "__main__":
    unittest.main()
