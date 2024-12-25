import logging
import os

import discord
from discord.errors import NotFound

from arsbot.core.db import bot_session
from arsbot.models import PhpbbPostRequest


log = logging.getLogger("arsbot")


class UnknownPhpBBMode(Exception):
    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode

    def __str__(self) -> str:
        return f"Unhandled PHPBB mode: {self.mode}"


def _make_forum_post_embed(post_request):
    forum_url = os.environ["PHPBB_BASE_URL"]
    post_id = post_request["post_id"]
    moderate_url = f"{forum_url}/mcp.php?i=queue&mode=approve_details&p={post_id}"

    if post_request["mode"] == "unapproved_topics":
        subject = "Topic"
    elif post_request["mode"] == "unapproved_posts":
        subject = "Post"
    else:
        raise UnknownPhpBBMode(post_request["mode"])

    embed = discord.Embed(
        title=f"airraidsirens.net {subject} Approval ({post_id})",
        type="rich",
        description="",
        url=moderate_url,
        timestamp=post_request["post_time"].datetime,
        color=0x00FBFF,
    )
    embed.add_field(
        name="Username",
        value=post_request["author_name"],
        inline=False,
    )
    embed.add_field(
        name="IP Address",
        value=post_request["post_ip_address"],
        inline=False,
    )
    embed.add_field(
        name="IP Location & Provider",
        value=f"{post_request['post_ip_location']} | {post_request['post_ip_organization']}",
        inline=False,
    )
    embed.add_field(
        name="Groups",
        value=post_request["user_group_list"],
        inline=False,
    )
    embed.add_field(
        name="Post Count",
        value=post_request["user_post_count"],
        inline=False,
    )
    embed.add_field(
        name="Warning Count",
        value=post_request["user_warning_count"],
        inline=False,
    )
    embed.add_field(
        name="Forum Name",
        value=post_request["forum_name"],
        inline=False,
    )
    embed.add_field(
        name="Topic Name",
        value=post_request["topic_name"],
        inline=False,
    )

    if post_request["mode"] == "unapproved_posts":
        last_approved_post_date = post_request.get("last_approved_post_date")
        if last_approved_post_date:
            last_approved_post_date_value = (
                f"<t:{int(last_approved_post_date.timestamp())}>"
            )
        else:
            last_approved_post_date_value = (
                "Failed to find most recently approved reply. Check yourself!"
            )

        embed.add_field(
            name="Last time post was approved in topic",
            value=last_approved_post_date_value,
            inline=False,
        )

    embed.add_field(
        name="Post Content",
        value=post_request["post_text"][:200],
        inline=False,
    )
    return embed


async def get_requests_from_channel(client, channel, view):
    """
    Syncs bot-generated phpbb moderation messages from our database with a Discord view
    so the buttons can be re-connected to the handle_approve and handle_deny callbacks.
    """
    known_request_ids = {}

    with bot_session() as session:
        async for message in channel.history():
            post_request = (
                session.query(PhpbbPostRequest)
                .filter_by(discord_message_id=message.id)
                .one_or_none()
            )

            if not post_request:
                log.info(
                    f"Found message {message.id} in <#{channel.id}> not attached to a db entry, deleting"
                )
                await message.delete()
                continue

            known_request_ids[post_request.post_id] = post_request
            client.add_view(view, message_id=post_request.discord_message_id)

    return known_request_ids


async def make_and_store_discord_request_message(post_request, channel, view):
    """
    Creates a new Discord message for a phpbb post requests then stores it in our database.
    """
    embed = _make_forum_post_embed(post_request)

    is_for_new_topic = post_request["mode"] == "unapproved_topics"
    item_type = "topic" if is_for_new_topic else "post"

    log.debug(f'Creating and sending new {item_type} request {post_request["post_id"]}')

    message = await channel.send(embed=embed, view=view)

    post_request_record = PhpbbPostRequest(
        author_id=post_request["author_id"],
        author_name=post_request["author_name"],
        author_url=post_request["author_url"],
        forum_name=post_request["forum_name"],
        forum_url=post_request["forum_url"],
        post_id=post_request["post_id"],
        post_ip_address=post_request["post_ip_address"],
        post_ip_hostname=post_request["post_ip_hostname"],
        post_ip_location=post_request["post_ip_location"],
        post_ip_organization=post_request["post_ip_organization"],
        post_text=post_request["post_text"],
        post_time=post_request["post_time"].datetime,
        topic_name=post_request["topic_name"],
        topic_url=post_request["topic_url"],
        user_group_list=post_request["user_group_list"],
        user_join_date=post_request["user_join_date"].datetime,
        user_post_count=post_request["user_post_count"],
        user_warning_count=post_request["user_warning_count"],
        is_for_new_topic=is_for_new_topic,
        time_created=post_request["post_time"].datetime,
        discord_message_id=message.id,
        discord_channel_id=message.channel.id,
        discord_guild_id=message.guild.id,
    )

    with bot_session() as session:
        session.add(post_request_record)
        session.commit()


async def purge_handled_requests(known_post_ids, channel):
    """
    Delete records where the request was handled through the web ui.
    """
    with bot_session() as session:
        handled_requests = (
            session.query(PhpbbPostRequest)
            .filter(
                ~PhpbbPostRequest.post_id.in_(list(known_post_ids)),
                PhpbbPostRequest.discord_channel_id == channel.id,
            )
            .filter(PhpbbPostRequest.time_resolved.is_(None))
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
