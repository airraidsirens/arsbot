from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import asyncio
import logging

import pytest

from arsbot.core.db import bot_session
from arsbot.discord.mediawiki.task import handle_automod_requests
from arsbot.discord.utils import task_state
from arsbot.models import MediaWikiAccountRequest


@dataclass
class DiscordUser:
    display_name: str
    id: str


class DiscordClient:
    def __init__(self):
        self.user = DiscordUser(
            display_name="arsbot",
            id="arsbot",
        )


task_state.client = DiscordClient()


class Writer:
    def __init__(self):
        self._records = []

    async def __call__(self, text: str) -> None:
        self._records.append(text)

        await asyncio.sleep(0.0)

    def clear(self) -> None:
        self._records = []

    @property
    def records(self) -> str:
        return self._records


class _process_account_request:
    def __call__(
        self, request: MediaWikiAccountRequest, approved: int, reviewer_name: str
    ) -> bool:
        return True


TASK_PATH = "arsbot.discord.mediawiki.task"


@pytest.fixture(autouse=True)
def _patched_process_account_request():
    with patch(
        TASK_PATH + ".process_account_request", new_callable=_process_account_request
    ) as patched:
        yield patched


@pytest.fixture(autouse=True)
def _patched_send_to_debug():
    with patch(TASK_PATH + ".send_to_debug", new_callable=Writer) as patched:
        yield patched


@pytest.fixture(autouse=True)
def _patched_send_to_wiki_log():
    with patch(TASK_PATH + ".send_to_wiki_log", new_callable=Writer) as patched:
        yield patched


@pytest.mark.asyncio
async def test_handle_automod_requests(caplog, _patched_send_to_wiki_log):
    task_state.last_wiki_automod_execute_report = None

    arsbot_log = logging.getLogger("arsbot")
    arsbot_log.level = logging.DEBUG
    arsbot_log.propagate = True

    caplog.set_level(logging.DEBUG)

    now = datetime.now(timezone.utc)
    three_days_ago = now - timedelta(days=3)

    request = MediaWikiAccountRequest(
        id=1,
        acrid=2,
        username="username_value",
        name="name_value",
        email="email_value",
        biography="biography_value <br />",
        discord_message_id=3,
        discord_channel_id=4,
        discord_guild_id=5,
        request_url="request_url_value",
        action=6,
        handled_by_id=7,
        handled_by_name="handled_by_name_value",
        automod_spam_categories="HAS_HTML",
        automod_manual_review_set_at=None,
        time_resolved=None,
        time_created=three_days_ago,
    )
    with bot_session() as session:
        session.add(request)
        session.commit()

    await handle_automod_requests()

    assert len(caplog.records) == 1
    assert caplog.records[0].message == "in handle_automod_requests: 1"
    caplog.clear()

    assert len(_patched_send_to_wiki_log.records) == 1
    assert (
        _patched_send_to_wiki_log.records[0]
        == "Wiki account for username_value denied by arsbot"
    )
    _patched_send_to_wiki_log.clear()
