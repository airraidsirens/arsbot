import functools
import logging

import discord

from .moderate_post import (
    handle_forum_ban,
    handle_forum_post,
)


log = logging.getLogger("arsbot")
_PHPBB_DISAPPROVE_REASONS = {
    1: "The message contains links to illegal or pirated software.",
    2: "Advertising for a website or another product.",
    3: "The reported message is off topic.",
    4: "Does not fit into any other category.",
    5: "The post in question is a duplicate.",
    6: "Does not meet posting standards.",
}


class PostRejectionReasonDropdown(discord.ui.Select):
    def __init__(self, set_rejection_reason_category):
        self.set_rejection_reason_category = set_rejection_reason_category

        options = []

        for reason_id, reason_string in _PHPBB_DISAPPROVE_REASONS.items():
            options.append(
                discord.SelectOption(
                    label=reason_string,
                    value=reason_id,
                )
            )

        super().__init__(
            placeholder="Select a disapprove reason",
            custom_id="post_rejection_reason_dropdown",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        disapprove_reason = self.values[0]

        await self.set_rejection_reason_category(interaction, self, disapprove_reason)


class ReasonModal(discord.ui.Modal, title="Disapprove Reason"):
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="This will be displayed to the poster, on top of the disapproval category.",
        required=False,
        style=discord.TextStyle.paragraph,
    )


class ReasonModalWithconfirm(discord.ui.Modal, title="Confirm Ban"):
    confirm_text = discord.ui.TextInput(
        label="Confirm",
        placeholder="Type CONFIRM to issue ban.",
        required=True,
        style=discord.TextStyle.short,
    )

    public_ban_reason = discord.ui.TextInput(
        label="Ban Reason Shown To User",
        placeholder="Optional",
        required=False,
        style=discord.TextStyle.paragraph,
    )


async def on_post_approval_submit(
    interaction: discord.Interaction, moderator_response: dict
):
    log.debug("on_post_approval_submit")

    moderator_response["deny_reason_message"] = ""
    moderator_response["rejection_reason_category"] = ""

    try:
        await handle_forum_post(
            discord_message_id=interaction.message.id,
            approved=True,
            reviewer_id=interaction.user.id,
            reviewer_name=interaction.user.display_name,
            interaction=interaction,
            moderator_response=moderator_response,
        )
    except Exception:
        log.exception("Failed to run handle_forum_post")


async def on_reason_submit(interaction: discord.Interaction, moderator_response: dict):
    log.debug("on_reason_submit")

    deny_reason_message = interaction.data["components"][0]["components"][0]["value"]
    moderator_response["deny_reason_message"] = deny_reason_message

    log.debug(moderator_response)

    try:
        await handle_forum_post(
            discord_message_id=interaction.message.id,
            approved=False,
            reviewer_id=interaction.user.id,
            reviewer_name=interaction.user.display_name,
            interaction=interaction,
            moderator_response=moderator_response,
        )
    except Exception:
        log.exception("Failed to run handle_forum_post")


async def on_ban_submit(interaction: discord.Interaction, moderator_response: dict):
    log.debug("on_ban_submit")

    confirm_message = interaction.data["components"][0]["components"][0]["value"]
    public_ban_reason = interaction.data["components"][1]["components"][0]["value"]

    if confirm_message != "CONFIRM":
        await interaction.response.send_message(
            "You must specify CONFIRM in the previous form.",
            ephemeral=True,
            delete_after=10,
        )
        return

    moderator_response["public_ban_reason"] = public_ban_reason or ""
    moderator_response["deny_reason_message"] = ""

    log.debug(moderator_response)

    try:
        await handle_forum_post(
            discord_message_id=interaction.message.id,
            approved=False,
            reviewer_id=interaction.user.id,
            reviewer_name=interaction.user.display_name,
            interaction=interaction,
            moderator_response=moderator_response,
        )
    except Exception:
        log.exception("Failed to run on_ban_submit for handle_forum_post")
        return

    try:
        await handle_forum_ban(
            discord_message_id=interaction.message.id,
            reviewer_id=interaction.user.id,
            reviewer_name=interaction.user.display_name,
            interaction=interaction,
            moderator_response=moderator_response,
        )
    except Exception:
        log.exception("Failed to run on_ban_submit for handle_forum_ban")
        return


class ModeratePostView(discord.ui.View):
    def __init__(self, *, timeout, handle_phpbb_post_moderation_action):
        super().__init__(timeout=timeout)

        self.handle_phpbb_post_moderation_action = handle_phpbb_post_moderation_action

        self.rejection_reason_category = None

        self.dropdown = PostRejectionReasonDropdown(
            set_rejection_reason_category=self.set_rejection_reason_category
        )

        self.add_item(self.dropdown)

    async def set_rejection_reason_category(
        self,
        interaction: discord.Interaction,
        select: PostRejectionReasonDropdown,
        category: int,
    ):
        self.rejection_reason_category = category

        await interaction.response.defer()

        # select.view.children[1].disabled = False
        # select.view.children[2].value = category

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="phpbb_row_0_approve",
        disabled=False,
    )
    async def handle_approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.debug("handle approve!")

        moderator_response = {
            "approved": True,
            "discord_message_id": interaction.message.id,
            "reviewer_id": interaction.user.id,
            "reviewer_name": interaction.user.display_name,
        }

        await on_post_approval_submit(interaction, moderator_response)

        # await interaction.response.defer()

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.secondary,
        custom_id="phpbb_row_0_deny",
        disabled=False,
    )
    async def handle_deny(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.debug("handle deny!")

        if self.rejection_reason_category is None:
            await interaction.response.send_message(
                "You must specify a rejection category.",
                ephemeral=True,
                delete_after=10,
            )
            return

        moderator_response = {
            "approved": False,
            "discord_message_id": interaction.message.id,
            "rejection_reason_category": self.rejection_reason_category,
            "reviewer_id": interaction.user.id,
            "reviewer_name": interaction.user.display_name,
        }

        modal2 = ReasonModal()
        modal2.on_submit = functools.partial(
            on_reason_submit, moderator_response=moderator_response
        )

        await interaction.response.send_modal(modal2)
        await interaction.response.defer()

    @discord.ui.button(
        label="Deny & Ban",
        style=discord.ButtonStyle.danger,
        custom_id="phpbb_row_0_deny_and_ban",
        disabled=False,
    )
    async def handle_deny_and_ban(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.debug("handle deny AND ban!")

        if self.rejection_reason_category is None:
            await interaction.response.send_message(
                "You must specify a rejection category.",
                ephemeral=True,
                delete_after=10,
            )
            return

        moderator_response = {
            "approved": False,
            "discord_message_id": interaction.message.id,
            "rejection_reason_category": self.rejection_reason_category,
            "reviewer_id": interaction.user.id,
            "reviewer_name": interaction.user.display_name,
        }

        modal2 = ReasonModalWithconfirm()
        modal2.on_submit = functools.partial(
            on_ban_submit, moderator_response=moderator_response
        )

        await interaction.response.send_modal(modal2)
        await interaction.response.defer()
