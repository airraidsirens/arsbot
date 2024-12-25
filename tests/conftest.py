from pathlib import Path
from unittest.mock import patch
import os
import tempfile

import pytest


@pytest.fixture
def bot_data_dir():
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        yield temp_dir


class Unset:
    pass


@pytest.fixture(autouse=True, scope="function")
def bot_env_config():
    test_config = {
        "WIKI_BASE_URL": "https://wiki.airraidsirens.net",
        "WIKI_USERNAME": "default",
        "WIKI_PASSWORD": "default",
        "DISCORD_BOT_TOKEN": "default",
        "DISCORD_BOT_GUILD_IDS": "0000000000000000001",
        "DISCORD_BOT_DEBUG_CHANNEL": "0000000000000000002",
        "DISCORD_WIKI_ACCOUNT_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000003",
        "DISCORD_WIKI_ACCOUNT_REQUESTS_STATS_CHANNEL_ID": "0000000000000000004",
        "DISCORD_WIKI_LOGS_CHANNEL_ID": "0000000000000000004",
        "DISCORD_FORUM_POST_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000005",
        "DISCORD_FORUM_POST_REQUESTS_STATS_CHANNEL_ID": "0000000000000000007",
        "DISCORD_FORUM_TOPIC_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000006",
        "DISCORD_FORUM_TOPIC_REQUESTS_STATS_CHANNEL_ID": "0000000000000000007",
        "DISCORD_FORUM_LOGS_CHANNEL_ID": "0000000000000000007",
        "ERROR_LOG_DISCORD_URL": "https://invalid",
        "BOT_SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "ROLE_NAME": "default",
        "PHPBB_BASE_URL": "https://airraidsirens.net/forums",
        "PHPBB_USERNAME": "testuser",
        "PHPBB_PASSWORD": "testpass",
        "SENTRY_DSN": "default",
        "SENTRY_ENVIRONMENT": "default",
        "VOICE_LOG_CHANNELS": "default",
        "CONNECT_DISCONNECT_LOG_CHANNELS": "default",
    }
    default_keys = set(test_config.keys())

    old_env = {}

    def _set_value(key, value):
        old_env[key] = os.environ.get(key) or Unset
        os.environ[key] = value

    for key, value in test_config.items():
        _set_value(key, value)

    yield _set_value

    def _unset_value(key):
        if key in default_keys and old_env[key] is not Unset:
            os.environ[key] = old_env[key]
        else:
            del os.environ[key]

    for key in test_config.keys():
        _unset_value(key)


class NullTimeSleep:
    def __call__(self, time_to_sleep: int | float):
        pass


@pytest.fixture(autouse=True, scope="function")
def skip_sleep():
    with patch("time.sleep", new_callable=NullTimeSleep) as patched_time_sleep:
        yield patched_time_sleep


def read_test_file(filename: str) -> str:
    here = Path(__file__).parent
    filepath = here / "data" / filename
    return filepath.read_text()
