from datetime import datetime, timezone
import asyncio
import os
import re

import pytest
import responses

from arsbot.core.db import bot_session
from arsbot.discord import utils as discord_utils
from arsbot.discord.mediawiki.moderate_account import handle_mediawiki_account
from arsbot.models import MediaWikiAccountRequest
from arsbot.models.base import BotBase

from tests.conftest import read_test_file


class MessageCounter:
    def __init__(self):
        self._count = 0

    def incr(self) -> int:
        self._count += 1
        return self._count


message_counter = MessageCounter()


class DiscordMessage:
    def __init__(self, message_id: int, channel_id: int, text: str):
        self._message_id = message_id
        self._channel_id = channel_id
        self._text = text
        self._deleted = False

    async def delete(self) -> None:
        await asyncio.sleep(0)

        assert self._deleted is False

        self._deleted = True


class DiscordResponse:
    def __init__(self):
        self._messages = []

    async def send_message(self, message, /, **kwargs) -> None:
        message_id = message_counter.incr()

        self._messages.append((message_id, message, kwargs))
        await asyncio.sleep(0)


class DiscordInteraction:
    def __init__(self, response):
        self._response = response
        self._message = DiscordMessage(
            message_id=0,
            channel_id=0,
            text="",
        )

    @property
    def response(self) -> DiscordResponse:
        return self._response

    @property
    def message(self):
        return self._message


class DiscordChannel:
    def __init__(self, channel_id: int | str):
        self._channel_id = int(channel_id)
        self._messages = {}

    async def send(self, text):
        await asyncio.sleep(0)

        message_id = message_counter.incr()

        self._messages[message_id] = DiscordMessage(
            message_id=message_id,
            channel_id=self._channel_id,
            text=text,
        )


class DiscordClient:
    def __init__(self):
        self._channels = {
            "1": DiscordChannel("1"),
            "2": DiscordChannel("2"),
        }

    async def fetch_channel(self, channel_id):
        await asyncio.sleep(0)
        return self._channels.get(channel_id)


@pytest.mark.asyncio
async def test_handle_mediawiki_account_unknown_request_id(
    bot_data_dir, bot_env_config
):
    discord_client = DiscordClient()
    interaction = DiscordInteraction(response=DiscordResponse())

    test_config = {
        "BOT_SQLALCHEMY_DATABASE_URI": f"sqlite:///{bot_data_dir}/testing.db",
        "DISCORD_BOT_DEBUG_CHANNEL": "1",
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

    discord_utils.client = discord_client

    await handle_mediawiki_account(
        discord_message_id=1,
        approved=True,
        reviewer_id=1,
        reviewer_name="pytest",
        interaction=interaction,
        button=None,  # discord.ui.Button,
    )

    assert interaction.response._messages == [
        (
            1,
            "An error occured while looking up the request: request with message id not found",
            {
                "ephemeral": True,
                "delete_after": 10,
            },
        )
    ]

    assert list(discord_client._channels["1"]._messages.keys()) == [2]
    message = discord_client._channels["1"]._messages[2]
    assert message._message_id == 2
    assert message._channel_id == 1
    assert message._text == (
        "handle_mediawiki_account: Unable to find request for 1. " "Received by pytest."
    )


def _get_wiki_index_callback(request):
    status_code = 200
    headers = {}
    content = ""

    return (status_code, headers, content)


def _get_wiki_login_callback(request):
    status_code = 200
    headers = {}
    content = read_test_file("wiki_login_form.html")

    return (status_code, headers, content)


def _post_wiki_login_callback(request):
    status_code = 200
    headers = {}
    content = read_test_file("wiki_login_success.html")

    return (status_code, headers, content)


def _get_wiki_confirm_account_callback(request):
    status_code = 200
    headers = {}
    content = ""

    return (status_code, headers, content)


def _post_wiki_confirm_account_callback(request):
    status_code = 200
    headers = {}
    content = ""

    return (status_code, headers, content)


def _post_wiki_confirm_account_not_found_callback(request):
    status_code = 404
    headers = {}
    content = ""

    return (status_code, headers, content)


@pytest.mark.asyncio
@responses.activate
@pytest.mark.parametrize("approved", [True, False])
async def test_handle_mediawiki_handle_account_request(
    bot_data_dir, bot_env_config, approved
):
    discord_client = DiscordClient()
    interaction = DiscordInteraction(response=DiscordResponse())

    test_config = {
        "BOT_SQLALCHEMY_DATABASE_URI": f"sqlite:///{bot_data_dir}/testing.db",
        "DISCORD_BOT_DEBUG_CHANNEL": "1",
        "DISCORD_WIKI_LOGS_CHANNEL_ID": "2",
        "WIKI_BASE_URL": "https://wiki.airraidsirens.net",
        "WIKI_USERNAME": "wiki_username",
        "WIKI_PASSWORD": "wiki_password",
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

    discord_utils.client = discord_client

    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/",
        callback=_get_wiki_index_callback,
    )

    params = {
        "title": "Special:UserLogin",
    }
    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/index.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_wiki_login_callback,
    )

    responses.add_callback(
        responses.POST,
        url=re.compile(r"https://wiki\.airraidsirens\.net/Special:UserLogin\?.*$"),
        callback=_post_wiki_login_callback,
    )

    params = {
        "title": "Special:ConfirmAccounts/authors",
        "acrid": 2,
    }
    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/index.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_wiki_confirm_account_callback,
    )

    responses.add_callback(
        responses.POST,
        url="https://wiki.airraidsirens.net/Special:ConfirmAccounts/authors",
        callback=_post_wiki_confirm_account_callback,
    )

    await handle_mediawiki_account(
        discord_message_id=3,
        approved=approved,
        reviewer_id=1,
        reviewer_name="pytest",
        interaction=interaction,
        button=None,
    )

    assert interaction.response._messages == []

    wiki_logs_channel_id = os.environ["DISCORD_WIKI_LOGS_CHANNEL_ID"]
    wiki_logs_messages = list(
        discord_client._channels[wiki_logs_channel_id]._messages.keys()
    )
    assert len(wiki_logs_messages) == 1

    log_message_id = wiki_logs_messages[0]

    message = discord_client._channels[wiki_logs_channel_id]._messages[log_message_id]
    assert message._message_id == log_message_id
    assert message._channel_id == int(wiki_logs_channel_id)

    approved_str = "approved" if approved else "denied"
    assert message._text == (
        f"Wiki account for username_value {approved_str} by pytest"
    )


@pytest.mark.asyncio
@responses.activate
@pytest.mark.parametrize("approved", [True, False])
async def test_handle_mediawiki_account_request_failed(
    bot_data_dir, bot_env_config, approved
):
    discord_client = DiscordClient()
    interaction = DiscordInteraction(response=DiscordResponse())

    test_config = {
        "BOT_SQLALCHEMY_DATABASE_URI": f"sqlite:///{bot_data_dir}/testing.db",
        "DISCORD_BOT_DEBUG_CHANNEL": "1",
        "DISCORD_WIKI_LOGS_CHANNEL_ID": "2",
        "WIKI_BASE_URL": "https://wiki.airraidsirens.net",
        "WIKI_USERNAME": "wiki_username",
        "WIKI_PASSWORD": "wiki_password",
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

    discord_utils.client = discord_client

    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/",
        callback=_get_wiki_index_callback,
    )

    params = {
        "title": "Special:UserLogin",
    }
    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/index.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_wiki_login_callback,
    )

    responses.add_callback(
        responses.POST,
        url=re.compile(r"https://wiki\.airraidsirens\.net/Special:UserLogin\?.*$"),
        callback=_post_wiki_login_callback,
    )

    params = {
        "title": "Special:ConfirmAccounts/authors",
        "acrid": 2,
    }
    responses.add_callback(
        responses.GET,
        url="https://wiki.airraidsirens.net/index.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_wiki_confirm_account_callback,
    )

    responses.add_callback(
        responses.POST,
        url="https://wiki.airraidsirens.net/Special:ConfirmAccounts/authors",
        callback=_post_wiki_confirm_account_not_found_callback,
    )

    await handle_mediawiki_account(
        discord_message_id=3,
        approved=approved,
        reviewer_id=1,
        reviewer_name="pytest",
        interaction=interaction,
        button=None,
    )

    message_id = interaction.response._messages[0][0]
    assert interaction.response._messages == [
        (
            message_id,
            "An error occured while looking up the request: unexpected mediawiki response",
            {
                "delete_after": 10,
                "ephemeral": True,
            },
        )
    ]

    wiki_logs_channel_id = os.environ["DISCORD_WIKI_LOGS_CHANNEL_ID"]
    wiki_logs_messages = list(
        discord_client._channels[wiki_logs_channel_id]._messages.keys()
    )
    assert len(wiki_logs_messages) == 0

    channel = discord_client._channels[os.environ["DISCORD_BOT_DEBUG_CHANNEL"]]
    assert len(channel._messages) == 1
    message_id = list(channel._messages.keys())[0]
    message = channel._messages[message_id]
    assert message._message_id == message_id
    assert message._channel_id == channel._channel_id
    assert message._text == "Failed to process mediawiki account confirmation"
    assert message._deleted is False
