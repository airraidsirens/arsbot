import os

import discord

from .forum_stats import automod_forum_stats
from .wiki_stats import automod_wiki_stats
from ...bot_listener import tree
from ...utils import (
    get_guild_ids,
    is_command_guild,
)


for config_guild_id in get_guild_ids():

    @tree.command(
        name="stats-automod",
        description="Display automod debug statistics.",
        guild=discord.Object(id=config_guild_id),
    )
    async def stats_automod(interaction):
        guild_id = interaction.guild.id
        if not is_command_guild(guild_id):
            return

        channel_id = interaction.channel.id

        channel_config = {
            "forum_post": "DISCORD_FORUM_POST_REQUESTS_STATS_CHANNEL_ID",
            "forum_topic": "DISCORD_FORUM_TOPIC_REQUESTS_STATS_CHANNEL_ID",
            "wiki_account": "DISCORD_WIKI_ACCOUNT_REQUESTS_STATS_CHANNEL_ID",
        }

        for channel_type, key in channel_config.items():
            if not (value := os.environ.get(key)):
                continue

            config_channel_ids = list(map(lambda v: int(v), value.split(",")))

            for config_channel_id in config_channel_ids:
                if channel_id != config_channel_id:
                    continue

                if channel_type in ["forum_post", "forum_topic"]:
                    message = automod_forum_stats()
                elif channel_type in ["wiki_account"]:
                    message = automod_wiki_stats()

                await interaction.response.send_message(message)
                return
