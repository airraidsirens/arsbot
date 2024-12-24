from datetime import datetime, timezone
import os

import arrow
import discord

from ..bot_listener import tree
from ..db import bot_session
from ..mediawiki.channels import send_discord_account_request_message
from ..models import MediaWikiAccountRequest
from ..utils import (
    get_guild_ids,
    is_command_guild,
    is_wiki_stats_channel,
    send_to_wiki_log,
    task_state,
)


def get_href(acrid: int) -> str:
    wiki_url = os.environ["WIKI_BASE_URL"]
    href = f"{wiki_url}/index.php?title=Special:ConfirmAccounts/authors&acrid={acrid}&wpShowRejects=1"
    return href


for config_guild_id in get_guild_ids():

    @tree.command(
        name="review-wiki-account",
        description="Sends the request caught by automod to the review channel.",
        guild=discord.Object(id=config_guild_id),
    )
    @discord.app_commands.describe(acrid="Account Request ID")
    async def review_wiki_account(interaction, acrid: int):
        guild_id = interaction.guild.id
        if not is_command_guild(guild_id):
            print(f"not a stats guild: {guild_id=}")
            return

        channel_id = interaction.channel.id
        if not is_wiki_stats_channel(channel_id):
            print(f"not a stats channel: <#{channel_id}>")
            return

        with bot_session() as session:
            account_request = (
                session.query(MediaWikiAccountRequest)
                .filter_by(acrid=acrid)
                .one_or_none()
            )
            if not account_request:
                message = "Unknown account request id"
                await interaction.response.send_message(message)
                return

            if account_request.time_resolved:
                href = get_href(acrid)
                who = account_request.handled_by_name
                message = (
                    f"[account request {acrid}]({href}) was already resolved {who}"
                )
                await interaction.response.send_message(message)
                return

            if not account_request.automod_spam_categories:
                href = get_href(acrid)
                message = f"[account request {acrid}]({href}) is not marked by automod"
                await interaction.response.send_message(message)
                return

            if account_request.automod_manual_review_set_at:
                # TODO: show when
                href = get_href(acrid)
                who = account_request.automod_manual_review_set_by_name
                message = (
                    f"[account request {acrid}]({href}) was already marked by {who}"
                )
                await interaction.response.send_message(message)
                return

            account = {
                "RequestedTimestamp": arrow.get(account_request.time_created),
                "Username": account_request.username,
                "Name": account_request.name,
                "Email": account_request.email,
                "Biography": account_request.biography,
            }

            discord_message = await send_discord_account_request_message(
                acrid=acrid,
                account=account,
                channel=task_state.requests_channel,
                view=task_state.approval_view,
            )

            account_request.automod_manual_review_set_by_id = interaction.user.id
            account_request.automod_manual_review_set_by_name = (
                interaction.user.display_name
            )
            account_request.automod_manual_review_set_at = datetime.now(timezone.utc)
            account_request.discord_message_id = discord_message.id
            account_request.discord_channel_id = discord_message.channel.id
            account_request.discord_guild_id = discord_message.guild.id

            session.add(account_request)
            session.commit()

        message = f"{acrid} has been flagged for manual review by {interaction.user.display_name}"
        await send_to_wiki_log(message)

        message = f"{acrid} has been sent to <#{account_request.discord_channel_id}>"
        await interaction.response.send_message(message)
