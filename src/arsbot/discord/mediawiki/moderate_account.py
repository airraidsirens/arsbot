import arrow
import discord

from arsbot.core.db import bot_session
from arsbot.models import MediaWikiAccountRequest

from .api_client import process_account_request
from ..utils import (
    send_to_debug,
    send_to_wiki_log,
)


async def handle_mediawiki_account(
    *,
    discord_message_id: int,
    approved: bool,
    reviewer_id: int,
    reviewer_name: str,
    interaction: discord.Interaction,
    button: discord.ui.Button,
):
    # print('Handling mediawiki account....')
    action = "approve" if approved else "deny"

    with bot_session() as session:
        request = (
            session.query(MediaWikiAccountRequest)
            .filter_by(discord_message_id=discord_message_id)
            .one_or_none()
        )

        if not request:
            await interaction.response.send_message(
                "An error occured while looking up the request: request with message id not found",
                ephemeral=True,
                delete_after=10,
            )

            await send_to_debug(
                f"handle_mediawiki_account: Unable to find request for {discord_message_id}. "
                f"Received by {reviewer_name}."
            )
            return

        # print(f'Found account_request! {request}')

        account_processed = process_account_request(
            request=request,
            approved=approved,
            reviewer_name=reviewer_name,
        )

        if not account_processed:
            await interaction.response.send_message(
                "An error occured while looking up the request: unexpected mediawiki response",
                ephemeral=True,
                delete_after=10,
            )

            await send_to_debug("Failed to process mediawiki account confirmation")
            return

        request.time_resolved = arrow.utcnow().datetime
        request.action = 1 if approved else 0
        request.handled_by_id = reviewer_id
        request.handled_by_name = reviewer_name
        session.add(request)
        session.commit()

        action = "approved" if approved else "denied"
        message = f"Wiki account for {request.username} {action} by {reviewer_name}"

        await send_to_wiki_log(message)

        await interaction.message.delete()
