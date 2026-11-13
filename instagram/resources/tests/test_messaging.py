import json
import unittest

from instagram.resources import messaging
from instagram.tests.helpers import FakeClient


class SendMessageTests(unittest.TestCase):
    def test_payload(self):
        c = FakeClient({("POST", "1784/messages"): {"recipient_id": "r1", "message_id": "m1"}})
        result = messaging.send_message(c, " r1 ", "hello")
        self.assertEqual(result["message_id"], "m1")
        params = c.calls[0][2]
        self.assertEqual(json.loads(params["recipient"]), {"id": "r1"})
        self.assertEqual(json.loads(params["message"]), {"text": "hello"})

    def test_message_text_is_not_stripped(self):
        c = FakeClient({("POST", "1784/messages"): {}})
        messaging.send_message(c, "r1", "  hi  ")
        self.assertEqual(json.loads(c.calls[0][2]["message"])["text"], "  hi  ")

    def test_unicode(self):
        c = FakeClient({("POST", "1784/messages"): {}})
        messaging.send_message(c, "r1", "Selam çğış")
        self.assertEqual(json.loads(c.calls[0][2]["message"])["text"], "Selam çğış")

    def test_recipient_required(self):
        c = FakeClient()
        for bad in ("", "  ", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                messaging.send_message(c, bad, "hi")
        self.assertEqual(c.calls, [])

    def test_message_required(self):
        c = FakeClient()
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                messaging.send_message(c, "r1", bad)
        self.assertEqual(c.calls, [])


if __name__ == "__main__":
    unittest.main()
