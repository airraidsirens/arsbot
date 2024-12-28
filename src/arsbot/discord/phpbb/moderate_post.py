import logging

import arrow
import discord

from arsbot.core.db import bot_session
from arsbot.models import PhpbbPostRequest

from .api_client import (
    ban_user_by_username,
    moderate_post,
)
from ..utils import (
    send_to_debug,
    send_to_forum_log,
)


log = logging.getLogger("arsbot")


async def handle_forum_ban(
    *,
    discord_message_id: int,
    reviewer_id: int,
    reviewer_name: str,
    interaction: discord.Interaction,
    moderator_response: dict,
):
    with bot_session() as session:
        request = (
            session.query(PhpbbPostRequest)
            .filter_by(
                discord_message_id=discord_message_id,
            )
            .one_or_none()
        )

        if not request:
            await send_to_debug(
                f"handle_forum_ban: Unable to find request for {discord_message_id}. "
                f"Received by {reviewer_name}."
            )
            return

        print(f"Found PHPBB request: {request}")

        message = f"PHPBB user {request.author_name} has been banned by {reviewer_name}"

        response = ban_user_by_username(
            user_id=request.author_id,
            reviewer_name=reviewer_name,
            reason_shown=moderator_response["public_ban_reason"],
        )

        if response:
            await send_to_forum_log(message)
            request.action = 2
            session.add(request)
            session.commit()
        else:
            error_message = f"Failed to apply forum ban for {request.author_name}"
            await send_to_debug(error_message)


async def handle_forum_post(
    *,
    discord_message_id: int,
    approved: bool,
    reviewer_id: int,
    reviewer_name: str,
    interaction: discord.Interaction,
    moderator_response: dict,
):
    with bot_session() as session:
        request = (
            session.query(PhpbbPostRequest)
            .filter_by(
                discord_message_id=discord_message_id,
            )
            .one_or_none()
        )

        if not request:
            await interaction.response.send_message(
                "An error occured while looking up the request: request with message id not found",
                ephemeral=True,
                delete_after=10,
            )

            await send_to_debug(
                f"handle_forum_post: Unable to find request for {discord_message_id}. "
                f"Received by {reviewer_name}."
            )
            return

        print(f"Found PHPBB request: {request}")

        action = "approved" if approved else "denied"
        post_or_topic = "topic" if request.is_for_new_topic else "post"
        message = f"PHPBB {post_or_topic} for {request.author_name} {action} by {reviewer_name}"

        response = moderate_post(
            post_id=request.post_id,
            approve=approved,
            rejection_category=moderator_response["deny_reason_message"],
            rejection_reason=moderator_response["rejection_reason_category"],
        )

        await send_to_forum_log(message)

        request.time_resolved = arrow.utcnow().datetime
        request.action = 1 if approved else 0
        request.handled_by_id = reviewer_id
        request.handled_by_name = reviewer_name
        session.add(request)
        session.commit()

    if response:
        await interaction.message.delete()

    await interaction.response.defer()
