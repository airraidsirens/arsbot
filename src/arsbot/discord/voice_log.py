import datetime
import os

import discord


async def _safe_send(client: discord.Client, channel_id: int, embed: discord.Embed):
    try:
        channel = await client.fetch_channel(channel_id)
    except discord.errors.Forbidden as exc:
        print(f"Unable to fetch_channel for {channel_id}: {exc}")
        return

    try:
        await channel.send(embed=embed)
    except discord.errors.Forbidden as exc:
        print(f"Unable to channel.send for {channel_id}: {exc}")
        return


async def on_voice_state_update(client, member, before, after):
    monitor_channels = os.environ.get("VOICE_LOG_CHANNELS", "").split(",")

    channels_to_send_to = set()

    for guild_channel in member.guild.channels:
        if guild_channel.type != discord.ChannelType.text:
            continue

        if str(guild_channel.id) in monitor_channels:
            channels_to_send_to.add(guild_channel.id)

    if not channels_to_send_to:
        print("Skipping voice log, no where to send to")
        return

    if before.channel and after.channel:
        if before.channel.id == after.channel.id:
            print("streaming or something...")
            return

        embed = discord.Embed(
            title="Member changed voice channel",
            type="rich",
            description=f"**Before:** <#{before.channel.id}>\n**+After:** <#{after.channel.id}>",
            timestamp=datetime.datetime.utcnow(),
            color=0x4286F4,
        )
    elif before.channel and not after.channel:
        embed = discord.Embed(
            title="Member left voice channel",
            type="rich",
            description=f"<@{member.id}> left <#{before.channel.id}>",
            timestamp=datetime.datetime.utcnow(),
            color=0xDD5E53,
        )
    else:
        embed = discord.Embed(
            title="Member joined voice channel",
            type="rich",
            description=f"<@{member.id}> joined <#{after.channel.id}>",
            timestamp=datetime.datetime.utcnow(),
            color=0x53DDAD,
        )

    embed.set_author(
        name=member.name,
        icon_url=member.display_avatar,
    )

    embed.set_footer(text=f"ID: {member.id}")

    for channel_id in channels_to_send_to:
        await _safe_send(client=client, channel_id=channel_id, embed=embed)
