import logging
import os

from discord.errors import Forbidden
import requests

from .bot_listener import client


log = logging.getLogger("arsbot")


class TaskState:
    def __init__(self):
        self.client = None
        self.requests_channel = None
        self.last_non_bot_message_check = None
        self.last_mediawiki_sync = None
        self.approval_view = None
        self.last_wiki_automod_execute_report = None

    def try_check_non_bot_messages(self, now: int, frequency: int) -> bool:
        if (
            not self.last_non_bot_message_check
            or now - self.last_non_bot_message_check >= frequency
        ):
            self.last_non_bot_message_check = now
            return True

        return False


task_state = TaskState()


async def send_to_debug(message):
    channel_id = os.environ["DISCORD_BOT_DEBUG_CHANNEL"]
    channel = await client.fetch_channel(channel_id)
    await channel.send(message)


async def send_to_wiki_log(message):
    channel_id = os.environ["DISCORD_WIKI_LOGS_CHANNEL_ID"]
    channel = await client.fetch_channel(channel_id)
    return await channel.send(message)


async def send_to_forum_log(message):
    channel_id = os.environ["DISCORD_FORUM_LOGS_CHANNEL_ID"]
    channel = await client.fetch_channel(channel_id)
    await channel.send(message)


def get_guild_ids() -> list[int]:
    if not (value := os.environ.get("DISCORD_BOT_GUILD_IDS")):
        return []

    config_guild_ids = list(map(lambda v: int(v), value.split(",")))

    return config_guild_ids


def is_command_guild(guild_id: int) -> bool:
    for config_guild_id in get_guild_ids():
        if guild_id == config_guild_id:
            return True

    return False


def is_wiki_stats_channel(channel_id: int) -> bool:
    if not (value := os.environ.get("DISCORD_WIKI_ACCOUNT_REQUESTS_STATS_CHANNEL_ID")):
        return False

    config_channel_ids = list(map(lambda v: int(v), value.split(",")))

    for config_channel_id in config_channel_ids:
        if channel_id == config_channel_id:
            return True

    return False


async def send_to_connect_channels(message, **kwargs):
    if not (
        channel_ids := os.environ.get("CONNECT_DISCONNECT_LOG_CHANNELS", "").split(",")
    ):
        return

    for channel_id in channel_ids:
        channel = await client.fetch_channel(channel_id)
        await channel.send(message, **kwargs)


def send_to_error(message):
    log.error(message)

    webhook_url = os.environ.get("ERROR_LOG_DISCORD_URL")
    if not webhook_url:
        return

    response = requests.post(
        webhook_url,
        params={"wait": False},
        json={
            "content": message,
            "username": "ARS Bot Exception",
        },
    )
    log.error(response.status_code)


async def delete_non_bot_messages(client, channel):
    """
    Deletes all messages in a given channel that were not authored by the current bot or Discord itself.
    """
    async for message in channel.history():
        if client.user.id == message.author.id or message.author.system:
            continue

        try:
            await message.delete()
            await send_to_debug(
                f"Removed message {message.id} by {message.author.display_name} from <#{message.channel.id}>."
            )
        except Forbidden:
            await send_to_debug(
                f"Unable to remove message {message.id} from {channel.name}: "
                "Missing ~Permissions.manage_messages"
            )
