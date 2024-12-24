import logging
import os

import discord
from discord.errors import NotFound

from ..db import bot_session
from ..models import MediaWikiAccountRequest


log = logging.getLogger("arsbot")


def _make_embed(acrid, account):
    wiki_url = os.environ["WIKI_BASE_URL"]
    request_url = (
        f"{wiki_url}/index.php?title=Special:ConfirmAccounts/authors&acrid={acrid}"
    )

    embed = discord.Embed(
        title=f"wiki.airraidsirens.net Account Request ({acrid})",
        type="rich",
        description="",
        url=request_url,
        timestamp=account["RequestedTimestamp"].datetime,
        color=0x00FBFF,
    )
    embed.add_field(
        name="Username",
        value=account["Username"],
        inline=True,
    )
    embed.add_field(
        name="Name",
        value=account["Name"],
        inline=True,
    )
    embed.add_field(
        name="Email",
        value=account["Email"],
        inline=False,
    )
    # Limit to first 200 characters
    embed.add_field(
        name="Biography",
        value=account["Biography"][:200],
        inline=False,
    )

    return embed


async def get_requests_from_channel(client, channel, view):
    """
    Syncs bot-generated wiki account messages from our database with a Discord view
    so the buttons can be re-connected to the handle_approve and handle_deny callbacks.
    """
    known_request_ids = set()

    with bot_session() as session:
        async for message in channel.history():
            account_request = (
                session.query(
                    MediaWikiAccountRequest.acrid,
                    MediaWikiAccountRequest.discord_message_id,
                )
                .filter_by(discord_message_id=message.id)
                .one_or_none()
            )

            if not account_request:
                log.debug(
                    f"Found message {message.id} not attached to a db entry, deleting"
                )
                await message.delete()
                continue

            known_request_ids.add(account_request.acrid)
            client.add_view(view, message_id=account_request.discord_message_id)

    return known_request_ids


async def send_discord_account_request_message(
    acrid, account, channel, view
) -> MediaWikiAccountRequest:
    """
    Creates a new Discord message for a MediaWiki account request then stores it
    in our database.
    """
    embed = _make_embed(acrid, account)
    log.debug(f"Creating and sending new record {acrid}")

    message = await channel.send(embed=embed, view=view)

    return message


async def purge_handled_requests(known_acrids, channel):
    """
    Delete records where the request was handled through the web ui.
    """
    with bot_session() as session:
        handled_requests = (
            session.query(MediaWikiAccountRequest)
            .filter(~MediaWikiAccountRequest.acrid.in_(list(known_acrids)))
            .filter(MediaWikiAccountRequest.time_resolved.is_(None))
            .all()
        )

        if handled_requests:
            log.debug(f"{len(handled_requests)} handled requests pending prune")

        for handled_request in handled_requests:
            log.debug(f"Removing handled request {handled_request}")

            try:
                message = await channel.fetch_message(
                    handled_request.discord_message_id
                )
                await message.delete()
            except NotFound:
                log.error(
                    f"Tried to delete a message but its gone ({handled_request.discord_message_id}) {handled_request}"
                )

            session.delete(handled_request)
            session.commit()
