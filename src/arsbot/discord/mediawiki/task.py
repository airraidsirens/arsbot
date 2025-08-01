from datetime import datetime, timedelta, timezone
import asyncio
import logging
import os
import time

import arrow
import discord
from aiohttp.client_exceptions import ClientOSError
from discord.errors import DiscordServerError

from arsbot.core.db import bot_session
from arsbot.core.lock import MESSAGE_LOCK
from arsbot.models import MediaWikiAccountRequest

from .api_client import (
    get_pending_accounts,
    PhpBBLoginFailed,
    process_account_request,
)
from .automod import get_spam_categories_for_request
from .channels import (
    get_requests_from_channel,
    purge_handled_requests,
    send_discord_account_request_message,
)
from .moderate_account import handle_mediawiki_account
from .view import ApprovalView
from ..bot_listener import BotClient
from ..const import (
    NON_BOT_CLEAR_FREQUENCY_SECONDS,
    SYNC_LOOP_DELAY,
)
from ..utils import (
    delete_non_bot_messages,
    send_to_debug,
    send_to_wiki_log,
    task_state,
)


log = logging.getLogger("arsbot")

MEDIA_WIKI_SYNC_FREQUENCY_SECONDS = 10


async def init_mediawiki_task(client: BotClient):
    task_state.client = client

    requests_channel = os.environ["DISCORD_WIKI_ACCOUNT_REQUESTS_REACTION_CHANNEL_ID"]

    # Delete non-bot generated messages from the channel. Threads are OK as long as they're
    # parented to a message we created.
    task_state.requests_channel = await client.fetch_channel(requests_channel)

    task_state.approval_view = ApprovalView(
        timeout=None, handle_mediawiki_account=handle_mediawiki_account
    )


async def _process_new_account_request(acrid: int, href: str, account):
    account_request = MediaWikiAccountRequest(
        acrid=acrid,
        request_url=href,
        time_created=account["RequestedTimestamp"].datetime,
        username=account["Username"],
        name=account["Name"],
        email=account["Email"],
        biography=account["Biography"],
    )

    request = (
        account_request.username,
        account_request.email,
        account_request.biography,
        account_request.handled_by_name,
    )

    spam_categories = get_spam_categories_for_request(request)
    if spam_categories:
        account_request.automod_spam_categories = ",".join(
            [category.name for category in spam_categories]
        )

    if account_request.automod_spam_categories:
        wiki_url = os.environ["WIKI_BASE_URL"]
        request_url = f"{wiki_url}{href}"

        # request found in spam category
        text = f"[account request {acrid}]({request_url}) was detected by automod "
        text += f"with result {account_request.automod_spam_categories}.\n"
        text += f"Account will be autorejected in 48 hours, run `/review-wiki-account {acrid}` to send to the\n"
        text += "manual review channel instead."

        embed = discord.Embed(
            title="Automod",
            description=text,
            url=request_url,
            timestamp=account_request.time_created,
        )

        channel_id = os.environ["DISCORD_WIKI_LOGS_CHANNEL_ID"]
        channel = await task_state.client.fetch_channel(channel_id)
        discord_message = await channel.send(embed=embed)
    else:
        discord_message = await send_discord_account_request_message(
            acrid=acrid,
            account=account,
            channel=task_state.requests_channel,
            view=task_state.approval_view,
        )

    account_request.discord_message_id = discord_message.id
    account_request.discord_channel_id = discord_message.channel.id
    account_request.discord_guild_id = discord_message.guild.id

    with bot_session() as session:
        session.add(account_request)
        session.commit()


async def handle_automod_requests():
    # Find requests that haven't been touched
    # in 48 hours then reject the accounts.
    #
    # Once rejected, send a message to #wiki-logs
    # saying account has been rejected by automod.
    now = datetime.now(timezone.utc)
    now_ts = int(time.time())
    in_48h = now + timedelta(days=2)

    with bot_session() as session:
        last_ts = task_state.last_wiki_automod_execute_report

        if last_ts is not None and ((now_ts - last_ts) / 60) < 60:
            return

        task_state.last_wiki_automod_execute_report = now_ts

        account_requests = (
            session.query(MediaWikiAccountRequest)
            .filter(MediaWikiAccountRequest.automod_spam_categories.isnot(None))
            .filter(MediaWikiAccountRequest.automod_manual_review_set_at.is_(None))
            .filter(MediaWikiAccountRequest.time_created < in_48h)
            .filter(MediaWikiAccountRequest.time_resolved.is_(None))
            .all()
        )

        log.debug(f"in handle_automod_requests: {len(account_requests)}")

        reviewer_name = task_state.client.user.display_name
        reviewer_id = task_state.client.user.id

        for request in account_requests:
            if not process_account_request(
                request=request,
                approved=0,
                reviewer_name=reviewer_name,
            ):
                await send_to_debug("Failed to process mediawiki account confirmation")
                continue

            request.time_resolved = arrow.utcnow().datetime
            request.action = 0
            request.handled_by_id = reviewer_id
            request.handled_by_name = reviewer_name
            session.add(request)
            session.commit()

            message = f"Wiki account for {request.username} denied by {reviewer_name}"

            await send_to_wiki_log(message)


def _get_automod_requests():
    known_request_ids = set()

    with bot_session() as session:
        account_requests = (
            session.query(MediaWikiAccountRequest.acrid)
            .filter(MediaWikiAccountRequest.automod_spam_categories.isnot(None))
            .all()
        )

        for account_request in account_requests:
            known_request_ids.add(account_request.acrid)

    return known_request_ids


async def run_mediawiki_task_once(now: float):
    if task_state.try_check_non_bot_messages(now, NON_BOT_CLEAR_FREQUENCY_SECONDS):
        try:
            # log.debug('syncing non bot messages')
            await delete_non_bot_messages(
                task_state.client, task_state.requests_channel
            )
        except (DiscordServerError, ClientOSError) as exc:
            log.exception(f"Failed to call delete_non_bot_messages: {exc}")
            return

    if (
        task_state.last_mediawiki_sync
        and now - task_state.last_mediawiki_sync < MEDIA_WIKI_SYNC_FREQUENCY_SECONDS
    ):
        # TODO: Maybe return the amount of seconds we should wait in the main loop?
        await asyncio.sleep(SYNC_LOOP_DELAY)
        return

    # log.debug('syncing mediawiki')

    task_state.last_mediawiki_sync = now

    async with MESSAGE_LOCK:
        try:
            known_request_ids = await get_requests_from_channel(
                task_state.client,
                task_state.requests_channel,
                view=task_state.approval_view,
            )
        except (DiscordServerError, ClientOSError) as exc:
            log.exception(f"Failed to get channel requests: {exc}")
            return

        known_request_ids |= _get_automod_requests()

        try:
            pending_mediawiki_accounts = get_pending_accounts()
        except PhpBBLoginFailed as exc:
            log.exception(f"Failed to login to MediaWiki: {exc}")
            return

        known_acrids = set()
        for href, account in pending_mediawiki_accounts.items():
            acrid = account["acrid"]
            known_acrids.add(acrid)

            # Already tracked...
            if acrid in known_request_ids:
                continue

            await _process_new_account_request(
                acrid=acrid,
                href=href,
                account=account,
            )

        await purge_handled_requests(known_acrids, task_state.requests_channel)
        await handle_automod_requests()
