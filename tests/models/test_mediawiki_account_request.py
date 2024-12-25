from datetime import datetime, timezone

from arsbot.core.db import bot_session
from arsbot.models import MediaWikiAccountRequest
from arsbot.models.base import BotBase


def test_validate_config(bot_data_dir, bot_env_config):
    db_uri = "sqlite:///:memory:"

    test_config = {
        "BOT_SQLALCHEMY_DATABASE_URI": db_uri,
    }

    for key, value in test_config.items():
        bot_env_config(key, value)

    with bot_session() as session:
        BotBase.metadata.create_all(session.bind)

        request = MediaWikiAccountRequest(
            id=1,
            acrid=2,
            username="username_value",
            name="name_value",
            email="email_value",
            biography="biography_value",
            discord_message_id=3,
            discord_channel_id=4,
            discord_guild_id=5,
            request_url="request_url_value",
            time_created=datetime.now(timezone.utc),
            time_resolved=datetime.now(timezone.utc),
            action=6,
            handled_by_id=7,
            handled_by_name="handled_by_name_value",
        )
        session.add(request)
        session.commit()
        assert (
            f"{request}"
            == "<MediaWikiAccountRequest self.acrid=2 self.discord_message_id=3>"
        )
