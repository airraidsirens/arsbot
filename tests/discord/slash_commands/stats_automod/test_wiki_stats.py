from datetime import datetime, timezone

from sqlalchemy.orm import Session

from arsbot.core.db import bot_session
from arsbot.models import MediaWikiAccountRequest
from arsbot.models.base import BotBase
from arsbot.discord.slash_commands.stats_automod.wiki_stats import _get_spam_scores
from arsbot.utils.text_table import TextTable


def _make_generic_request(session: Session, acrid: int, biography: str) -> None:
    request = MediaWikiAccountRequest(
        acrid=acrid,
        username="test",
        name="test",
        email="test@example.com",
        biography=biography,
        discord_message_id=1,
        discord_channel_id=2,
        discord_guild_id=3,
        request_url="https://examplewiki/link",
        time_created=datetime.now(timezone.utc),
        time_resolved=datetime.now(timezone.utc),
        action=0,
        automod_spam_categories="HAS_HTML",
    )
    session.add(request)
    session.commit()


def test_automod_wiki_stats():
    with bot_session() as session:
        BotBase.metadata.create_all(session.bind)

        _make_generic_request(session, 1, "This has spam <br> test")

        text = _get_spam_scores(session=session, action=0)

    table = TextTable()

    table.set_header("AutoMod Stats")
    table.set_footer("End of Stats")

    table.add_key_value("action", "denied")
    table.add_key_value("total", 1)
    table.add_key_value("catch_%", 100.0)
    table.add_key_value("not_as_spam", 0)
    table.add_key_value("as_spam", 1)
    table.add_key_value("has_link", 0)
    table.add_key_value("has_non_ascii", 0)
    table.add_key_value("has_html", 1)

    message = table.str()

    assert message == text
