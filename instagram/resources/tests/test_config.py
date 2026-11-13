import dataclasses
import os
import unittest
from unittest import mock

from instagram.config import DEFAULT_API_VERSION, Config, load_config
from instagram.exceptions import ConfigError

ENV_KEYS = (
    "IG_ACCESS_TOKEN",
    "IG_NODE",
    "IG_GRAPH_API_VERSION",
    "FB_APP_ID",
    "FB_APP_SECRET",
)


class LoadConfigTests(unittest.TestCase):
    def _env(self, **values):
        env = {k: v for k, v in os.environ.items() if k not in ENV_KEYS}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_missing_token_raises(self):
        with self._env(IG_NODE="123"):
            with self.assertRaises(ConfigError) as cm:
                load_config()
        self.assertIn("IG_ACCESS_TOKEN", str(cm.exception))

    def test_blank_token_raises(self):
        with self._env(IG_ACCESS_TOKEN="   ", IG_NODE="123"):
            with self.assertRaises(ConfigError):
                load_config()

    def test_missing_node_raises(self):
        with self._env(IG_ACCESS_TOKEN="t"):
            with self.assertRaises(ConfigError) as cm:
                load_config()
        self.assertIn("IG_NODE", str(cm.exception))

    def test_node_me_is_rejected_case_insensitive(self):
        for value in ("me", "ME", " Me "):
            with self._env(IG_ACCESS_TOKEN="t", IG_NODE=value):
                with self.assertRaises(ConfigError, msg=value):
                    load_config()

    def test_defaults(self):
        with self._env(IG_ACCESS_TOKEN="t", IG_NODE="123"):
            cfg = load_config()
        self.assertEqual(cfg.access_token, "t")
        self.assertEqual(cfg.node, "123")
        self.assertEqual(cfg.api_version, DEFAULT_API_VERSION)
        self.assertEqual(cfg.app_id, "")
        self.assertEqual(cfg.app_secret, "")

    def test_values_are_stripped(self):
        with self._env(
            IG_ACCESS_TOKEN="  tok  ",
            IG_NODE=" 99 ",
            IG_GRAPH_API_VERSION=" v20.0 ",
            FB_APP_ID=" id ",
            FB_APP_SECRET=" sec ",
        ):
            cfg = load_config()
        self.assertEqual(
            (cfg.access_token, cfg.node, cfg.api_version, cfg.app_id, cfg.app_secret),
            ("tok", "99", "v20.0", "id", "sec"),
        )

    def test_blank_api_version_falls_back_to_default(self):
        with self._env(IG_ACCESS_TOKEN="t", IG_NODE="1", IG_GRAPH_API_VERSION="  "):
            self.assertEqual(load_config().api_version, DEFAULT_API_VERSION)


class ConfigTests(unittest.TestCase):
    def test_base_url(self):
        cfg = Config("t", "1", "v19.0", "", "")
        self.assertEqual(cfg.base_url, "https://graph.facebook.com/v19.0")

    def test_config_is_frozen(self):
        cfg = Config("t", "1", "v19.0", "", "")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.node = "2"


if __name__ == "__main__":
    unittest.main()
