import asyncio
import logging

import discord
from discord import app_commands


log = logging.getLogger("arsbot")


class BotState:
    def __init__(self):
        self.connected = False
        self.voice_state_update_hooks = []
        self.on_ready_hooks = []


bot_state = BotState()


async def sync_command_tree(self):
    from .utils import get_guild_ids

    log.info(f"Logged on as {self.user}")
    bot_state.connected = True

    while not self._command_tree:
        await asyncio.sleep(0.1)
        return await self.on_ready()

    for guild_id in get_guild_ids():
        await self._command_tree.sync(guild=discord.Object(id=guild_id))

    await asyncio.sleep(0.1)


class BotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._command_tree = None

    async def on_ready(self):
        for hook in bot_state.on_ready_hooks:
            await hook(self)

    def set_tree(self, tree: app_commands.CommandTree) -> None:
        self._command_tree = tree

    async def on_voice_state_update(self, member, before, after):
        for hook in bot_state.voice_state_update_hooks:
            await hook(self, member, before, after)


bot_state.on_ready_hooks.append(sync_command_tree)
discord.VoiceClient.warn_nacl = False
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = BotClient(intents=intents)
tree = app_commands.CommandTree(client)

client.set_tree(tree)

from . import slash_commands  # noqa: F401,E402
