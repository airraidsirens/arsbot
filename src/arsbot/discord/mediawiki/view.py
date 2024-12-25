import logging
import os

import discord

from arsbot.core.lock import MESSAGE_LOCK


log = logging.getLogger("arsbot")


def can_moderate(roles):
    approver_role = os.environ["ROLE_NAME"]
    for role in roles:
        if role.name == approver_role:
            return True

    return False


class ApprovalView(discord.ui.View):
    def __init__(self, *, timeout, handle_mediawiki_account):
        super().__init__(timeout=timeout)
        self.handle_mediawiki_account = handle_mediawiki_account

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="row_0_button_0_approve",
        disabled=False,
    )
    async def handle_approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.debug("handle approve!")

        approver_role = os.environ["ROLE_NAME"]

        if not can_moderate(interaction.user.roles):
            await interaction.response.send_message(
                f"Missing required discord role: {approver_role}",
                ephemeral=True,
                delete_after=10,
            )
            return

        async with MESSAGE_LOCK:
            await self.handle_mediawiki_account(
                discord_message_id=interaction.message.id,
                approved=True,
                reviewer_id=interaction.user.id,
                reviewer_name=interaction.user.display_name,
                interaction=interaction,
                button=button,
            )

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        custom_id="row_0_button_1_deny",
        disabled=False,
    )
    async def handle_deny(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.debug("handle deny!")

        approver_role = os.environ["ROLE_NAME"]

        if not can_moderate(interaction.user.roles):
            await interaction.response.send_message(
                f"Missing required discord role: {approver_role}",
                ephemeral=True,
                delete_after=10,
            )
            return

        async with MESSAGE_LOCK:
            await self.handle_mediawiki_account(
                discord_message_id=interaction.message.id,
                approved=False,
                reviewer_id=interaction.user.id,
                reviewer_name=interaction.user.display_name,
                interaction=interaction,
                button=button,
            )
