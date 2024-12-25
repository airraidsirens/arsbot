from datetime import datetime, timezone

from arsbot.core.db import bot_session
from arsbot.models import PhpbbPostRequest
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

        request = PhpbbPostRequest(
            id=1,
            author_id=2,
            author_name="author_name_value",
            author_url="author_url_value",
            forum_name="forum_name_value",
            forum_url="forum_url_value",
            post_id=3,
            post_ip_address="post_ip_address_value",
            post_ip_hostname="post_ip_hostname_value",
            post_ip_location="post_ip_location_value",
            post_ip_organization="post_ip_organization_value",
            post_text="post_text_value",
            post_time=datetime.now(timezone.utc),
            topic_name="topic_name_value",
            topic_url="topic_url_value",
            user_group_list="user_group_list_value",
            user_join_date=datetime.now(timezone.utc),
            user_post_count=4,
            user_warning_count=5,
            is_for_new_topic=6,
            discord_message_id=7,
            discord_channel_id=8,
            discord_guild_id=9,
            time_created=datetime.now(timezone.utc),
            time_resolved=datetime.now(timezone.utc),
            action=10,
            handled_by_id=11,
            handled_by_name="handled_by_name_value",
        )
        session.add(request)
        session.commit()
        assert (
            f"{request}"
            == "<PhpbbPostRequest self.post_id=3 self.is_for_new_topic=6 self.discord_message_id=7>"
        )
