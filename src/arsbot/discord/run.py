from datetime import datetime, timedelta, timezone
from io import BytesIO
import asyncio
import logging
import os
import sys
import time
import traceback
import uuid

from discord.errors import PrivilegedIntentsRequired
from discord.utils import MISSING
import discord
import sentry_sdk

from .bot_listener import (
    bot_state,
    client,
)
from .mediawiki.task import (
    init_mediawiki_task,
    run_mediawiki_task_once,
)
from .phpbb.task import (
    init_phpbb_task,
    run_phpbb_task_once,
)
from .utils import (
    send_to_connect_channels,
    send_to_error,
)
from .voice_log import on_voice_state_update
from ..utils.text_table import TextTable
from ..version import (
    GIT_VERSION,
    GIT_DATETIME,
    GIT_USER_NAME,
    GIT_USER_EMAIL,
    VERSION,
)


log = logging.getLogger("arsbot")
instance_id = str(uuid.uuid4())
started = time.time()


class TaskFinished(Exception):
    pass


async def _wait_for_connection():
    # Wait for the discord connection from the other coroutine
    while (
        client.http._global_over is MISSING
        or not client.user
        or not bot_state.connected
    ):
        await asyncio.sleep(0.1)


async def main_io_loop():
    """
    Main loop for doing all the things including:

    * Syncing account requests from MediaWiki
    * Syncing MediaWiki account requests to the #wiki-account-requests Discord channel
    * Removing non-bot and system messages from the #wiki-account-requests Discord channel
    """

    await _wait_for_connection()

    await init_mediawiki_task(client)
    await init_phpbb_task(client)

    while True:
        now = time.time()

        await run_mediawiki_task_once(now)
        await run_phpbb_task_once(now)

        await asyncio.sleep(0.1)


async def send_connect_message(local_client):
    log.info(f"Connected to Discord. instance_id:{instance_id}")

    table = TextTable()

    table.set_header("Connected to Discord")
    table.set_footer("End of connect info")

    table.add_key_value("instance_id", instance_id)
    table.add_key_value("python", sys.version)
    table.add_key_value("arsbot", VERSION)
    table.add_key_value("version", GIT_VERSION)
    table.add_key_value("timestamp", GIT_DATETIME)
    table.add_key_value("author_name", GIT_USER_NAME)
    table.add_key_value("author_email", GIT_USER_EMAIL)

    message = table.str()

    await send_to_connect_channels(message)


async def discord_runner():
    bot_token = os.environ["DISCORD_BOT_TOKEN"]

    # bot_state.on_ready_hooks.append(send_connect_message)

    async with client:
        await client.login(bot_token)

        try:
            await client.connect(reconnect=True)
        except PrivilegedIntentsRequired as exc:
            error_message = f"Failed to connect to Discord: {exc}"
            log.exception(error_message)

            send_to_error(error_message)


def runbot():
    log.debug("Starting runbot...")

    bot_state.voice_state_update_hooks.append(on_voice_state_update)

    if os.environ.get("SENTRY_DSN"):
        log.debug("Initializing Sentry")

        sentry_sdk.init(
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=1.0,
        )

        log.debug("Sentry initialized")

    background_tasks = set()
    loop = asyncio.get_event_loop()

    def task_done_callback(finished_task):
        log.info("TASK DONE!")

        task_name = finished_task.get_name()
        task_exc = finished_task.exception()
        func_name = finished_task.get_coro().cr_code.co_name

        utcnow = datetime.now(timezone.utc)
        uptime_duration_seconds = utcnow.timestamp() - started
        uptime_duration = str(timedelta(seconds=uptime_duration_seconds))

        discord_file = None

        if task_exc:
            exc_str = "".join(traceback.format_exception(task_exc))
            log.error(exc_str)

            error_message = f"An exception occured within {task_name} ({func_name})."

            exc_file = BytesIO(exc_str.encode("utf-8"))
            exc_file.name = f"arsbot_exception_{utcnow.isoformat()}.txt"
            discord_file = discord.File(
                exc_file,
                filename=exc_file.name,
                description="Python Coroutine Traceback",
            )
        else:
            error_message = (
                "An IO task has finished. "
                "This probably means the bot needs to be restarted."
            )

        table = TextTable()

        if func_name == "discord_runner":
            table.set_header("Disconnected from Discord")
            table.set_footer("End of disconnect info")
        else:
            table.set_header("Async Task Exception")
            table.set_footer("End of async task exception")

        table.add_key_value("instance_id", instance_id)
        table.add_key_value("reason", "task_done_callback received")
        table.add_key_value("uptime_duration", uptime_duration)
        table.add_key_value("error_message", error_message)

        message = table.str()

        async def wait_coro(message_to_send, file_to_send):
            await send_to_connect_channels(message_to_send, file=file_to_send)

        message_task = asyncio.create_task(wait_coro(message, discord_file))

        background_tasks.add(message_task)

        background_tasks.discard(finished_task)

        if func_name == "main_io_loop":
            main_io_loop_task = asyncio.create_task(main_io_loop())
            background_tasks.add(main_io_loop_task)

            # Requeue the task
            main_io_loop_task.add_done_callback(task_done_callback)

    async def create_tasks_func():
        task1 = asyncio.create_task(main_io_loop())
        background_tasks.add(task1)

        task1.add_done_callback(task_done_callback)

        task2 = asyncio.create_task(discord_runner())
        background_tasks.add(task2)

        task2.add_done_callback(background_tasks.discard)

        await asyncio.wait(background_tasks)

    async def run_keyboard_interrupt():
        uptime_duration_seconds = time.time() - started
        uptime_duration = str(timedelta(seconds=uptime_duration_seconds))

        reason = "Got keyboard interrupt, shutting down."

        basic_message = (
            f"{reason} "
            f"instance_id:{instance_id} "
            f"uptime duration:{uptime_duration}"
        )

        log.info(basic_message)

        table = TextTable()

        table.set_header("Disconnected from Discord")
        table.set_footer("End of disconnect info")

        table.add_key_value("instance_id", instance_id)
        table.add_key_value("reason", reason)
        table.add_key_value("uptime_duration", uptime_duration)

        message = table.str()

        keryboard_interrupt_tasks = set()
        coro = send_to_connect_channels(message)
        task = asyncio.create_task(coro)
        keryboard_interrupt_tasks.add(task)
        await asyncio.wait(keryboard_interrupt_tasks)

    try:
        loop.run_until_complete(create_tasks_func())
    except KeyboardInterrupt:
        loop.run_until_complete(run_keyboard_interrupt())
        return
