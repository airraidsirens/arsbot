import os


class ConfigError(Exception):
    """
    Raised when a required environment variable has not been set.

    If raised, set the entry in .env or as an environment variable directly.
    """

    def __init__(self, entry: str, how_to_fix: str):
        super().__init__((f"Missing config entry: {entry}\n" f"{how_to_fix}"))


def validate_config():
    config_entries = {
        # Discord settings
        "DISCORD_BOT_TOKEN": "See the #generating-a-discord-bot-token section in README.md",
        "DISCORD_BOT_DEBUG_CHANNEL": "See the #bot-debug-discord-channel section in README.md",
        "DISCORD_WIKI_ACCOUNT_REQUESTS_REACTION_CHANNEL_ID": (
            "See the #mediawiki-account-requests-discord-channel section in README.md"
        ),
        "DISCORD_WIKI_LOGS_CHANNEL_ID": "See the #mediawiki-logging-discord-channel section in README.md",
        "DISCORD_FORUM_POST_REQUESTS_REACTION_CHANNEL_ID": (
            "See the #phpbb-logging-discord-channel section in README.md"
        ),
        "DISCORD_FORUM_TOPIC_REQUESTS_REACTION_CHANNEL_ID": (
            "See the #phpbb-moderation-discord-channel section in README.md"
        ),
        "DISCORD_FORUM_LOGS_CHANNEL_ID": "See the #phpbb-moderation-discord-channel section in README.md",
        "ROLE_NAME": "The name of the role that can moderate wiki accounts",
        # MediaWiki settings
        "WIKI_BASE_URL": "See the #mediawiki-configuration section in README.md",
        "WIKI_USERNAME": "See the #mediawiki-configuration section in README.md",
        "WIKI_PASSWORD": "See the #mediawiki-configuration section in README.md",
    }

    for key, value in config_entries.items():
        if not os.environ.get(key):
            raise ConfigError(key, value)
