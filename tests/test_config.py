import os

import pytest

from arsbot.config import (
    ConfigError,
    validate_config,
)


def test_validate_config(bot_env_config):
    del os.environ["DISCORD_BOT_TOKEN"]

    with pytest.raises(ConfigError) as error:
        validate_config()

    assert error.value.args == (
        (
            "Missing config entry: DISCORD_BOT_TOKEN\n"
            "See the #generating-a-discord-bot-token section in README.md"
        ),
    )

    test_config = {
        "DISCORD_BOT_TOKEN": "test",
        "DISCORD_BOT_DEBUG_CHANNEL": "0000000000000000000",
        "DISCORD_WIKI_ACCOUNT_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000001",
        "DISCORD_WIKI_LOGS_CHANNEL_ID": "0000000000000000002",
        "DISCORD_FORUM_POST_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000003",
        "DISCORD_FORUM_TOPIC_REQUESTS_REACTION_CHANNEL_ID": "0000000000000000004",
        "DISCORD_FORUM_LOGS_CHANNEL_ID": "0000000000000000005",
        "ROLE_NAME": "test",
        "WIKI_BASE_URL": "https://wiki.airraidsirens.net",
        "WIKI_USERNAME": "arsbot",
        "WIKI_PASSWORD": "testpass",
    }

    for key, value in test_config.items():
        bot_env_config(key, value)

    assert validate_config() is None
