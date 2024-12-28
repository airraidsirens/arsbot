from datetime import datetime, timezone

from arsbot.core.db import bot_session
from arsbot.models import MediaWikiAccountRequest


def test_validate_config():
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
    with bot_session() as session:
        session.add(request)
        session.commit()

        assert (
            f"{request}"
            == "<MediaWikiAccountRequest self.acrid=2 self.discord_message_id=3>"
        )
