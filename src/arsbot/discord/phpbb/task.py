import asyncio
import logging
import os

from aiohttp.client_exceptions import ClientOSError
from discord.errors import DiscordServerError

from .channels import (
    get_requests_from_channel,
    make_and_store_discord_request_message,
    purge_handled_requests,
)
from .moderate_post import handle_forum_post
from .view import ModeratePostView
from ..bot_listener import BotClient
from ..const import (
    NON_BOT_CLEAR_FREQUENCY_SECONDS,
    SYNC_LOOP_DELAY,
)
from ..utils import delete_non_bot_messages
from ..lock import MESSAGE_LOCK
from ...phpbb.http import (
    load_posts_awaiting_approval,
    load_topics_awaiting_approval,
)


log = logging.getLogger("arsbot")


class TaskState:
    def __init__(self):
        self.client = None
        self.moderation_channel_topics = None
        self.moderation_channel_posts = None
        self.last_non_bot_message_check = None
        self.last_phpbb_sync = None
        self.forum_moderate_view = None


task_state = TaskState()
PHPBB_SYNC_FREQUENCY_SECONDS = 60


async def init_phpbb_task(client: BotClient):
    task_state.client = client

    moderation_channel_topics = os.environ[
        "DISCORD_FORUM_TOPIC_REQUESTS_REACTION_CHANNEL_ID"
    ]
    task_state.moderation_channel_topics = await client.fetch_channel(
        moderation_channel_topics
    )

    moderation_channel_posts = os.environ[
        "DISCORD_FORUM_POST_REQUESTS_REACTION_CHANNEL_ID"
    ]
    task_state.moderation_channel_posts = await client.fetch_channel(
        moderation_channel_posts
    )

    task_state.forum_moderate_view = ModeratePostView(
        timeout=None,
        handle_phpbb_post_moderation_action=handle_forum_post,
    )


async def _safe_delete(client: BotClient, channel) -> bool:
    try:
        await delete_non_bot_messages(client=client, channel=channel)

        return True
    except (DiscordServerError, ClientOSError) as exc:
        log.exception(
            f"Failed to call delete_non_bot_messages on moderation_channel_topics: {exc}"
        )

        return False


async def _sync_topic_approvals(now: float):
    try:
        known_request_ids = await get_requests_from_channel(
            client=task_state.client,
            channel=task_state.moderation_channel_topics,
            view=task_state.forum_moderate_view,
        )
    except (DiscordServerError, ClientOSError) as exc:
        log.exception(f"Failed to get channel requests: {exc}")
        return

    pending_topics = load_topics_awaiting_approval()

    known_post_ids = set()
    for post_request in pending_topics:
        post_id = post_request["post_id"]
        known_post_ids.add(post_id)

        # Already tracked...
        if post_id in known_request_ids:
            continue

        await make_and_store_discord_request_message(
            post_request=post_request,
            channel=task_state.moderation_channel_topics,
            view=task_state.forum_moderate_view,
        )

    await purge_handled_requests(known_post_ids, task_state.moderation_channel_topics)


async def _sync_post_approvals(now: float):
    try:
        known_request_ids = await get_requests_from_channel(
            client=task_state.client,
            channel=task_state.moderation_channel_posts,
            view=task_state.forum_moderate_view,
        )
    except (DiscordServerError, ClientOSError) as exc:
        log.exception(f"Failed to get channel requests: {exc}")
        return

    pending_topics = load_posts_awaiting_approval()

    known_post_ids = set()
    for post_request in pending_topics:
        post_id = post_request["post_id"]
        known_post_ids.add(post_id)

        # Already tracked...
        if post_id in known_request_ids:
            continue

        await make_and_store_discord_request_message(
            post_request=post_request,
            channel=task_state.moderation_channel_posts,
            view=task_state.forum_moderate_view,
        )

    await purge_handled_requests(known_post_ids, task_state.moderation_channel_posts)


async def run_phpbb_task_once(now: float):
    last_check = task_state.last_non_bot_message_check

    if not last_check or now - last_check >= NON_BOT_CLEAR_FREQUENCY_SECONDS:
        task_state.last_non_bot_message_check = now

        if not await _safe_delete(
            client=task_state.client, channel=task_state.moderation_channel_topics
        ):
            return

        if not await _safe_delete(
            client=task_state.client, channel=task_state.moderation_channel_posts
        ):
            return

    if (
        task_state.last_phpbb_sync
        and now - task_state.last_phpbb_sync < PHPBB_SYNC_FREQUENCY_SECONDS
    ):
        # TODO: Maybe return the amount of seconds we should wait in the main loop?
        await asyncio.sleep(SYNC_LOOP_DELAY)
        return

    # log.debug('syncing phpbb')

    task_state.last_phpbb_sync = now

    async with MESSAGE_LOCK:
        await _sync_topic_approvals(now)
        await _sync_post_approvals(now)
