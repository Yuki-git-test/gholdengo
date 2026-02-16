import time

import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from Constants.aesthetic import *
from Constants.giveaway import BLACKLISTED_ROLES, Extra_Entries
from Constants.vn_allstars_constants import KHY_USER_ID, VN_ALLSTARS_TEXT_CHANNELS
from utils.cache.global_variables import TESTING_GA
from utils.db.ga_db import (
    update_giveaway_message_id,
    update_giveaway_thread_id,
    upsert_giveaway,
)
from utils.essentials.role_checks import *
from utils.giveaway.giveaway_funcs import build_ga_embed, can_host_ga
from utils.giveaway.views import GiveawayButtonsView
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.parsers.duration import parse_total_duration

"""bot: commands.Bot,
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int,
    channel: discord.TextChannel,
    has_message: bool,
    host: discord.Member = None,
    image_link: str = None,"""


class GiveawayDetailsModal(Modal):
    """🍀 Modal for staff to enter requirements or special message"""

    def __init__(
        self,
        bot: commands.Bot,
        giveaway_type: str,
        duration: int,
        prize: str,
        winners: int,
        channel: discord.TextChannel,
        host: discord.Member,
        image_link: str,
    ):
        super().__init__(title="Giveaway Details")
        self.bot = bot
        self.giveaway_type = giveaway_type
        self.duration = duration
        self.prize = prize
        self.winners = winners
        self.channel = channel
        self.host = host
        self.image_link = image_link
        self.giveaway_message = TextInput(
            label="Giveaway message",
            required=True,
            max_length=2000,
            style=discord.TextStyle.paragraph,
            placeholder="Enter requirements or a special message (max 100 chars in placeholder)",
        )
        self.add_item(self.giveaway_message)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Step 1: Defer response
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            pretty_log("info", "✅ Modal submitted, response deferred")

            # Grab input giveaway message
            giveaway_message = self.giveaway_message.value

            # Insert giveaway into database
            try:
                giveaway_id = await upsert_giveaway(
                    bot=self.bot,
                    message_id=0,  # Placeholder, will update after sending message
                    host_id=self.host.id,
                    host_name=self.host.display_name,
                    giveaway_type=self.giveaway_type,
                    prize=self.prize,
                    ends_at=self.duration,
                    max_winners=self.winners,
                    channel_id=self.channel.id,
                    image_link=self.image_link,
                )
            except Exception as e:
                await interaction.followup.send(
                    "An error occurred while saving the giveaway to the database.",
                    ephemeral=True,
                )
                pretty_log(
                    "error",
                    f"Error inserting giveaway into database in modal submission: {e}",
                )
                return

            try:
                ga_embed, content = build_ga_embed(
                    host=self.host,
                    giveaway_type=self.giveaway_type,
                    prize=self.prize,
                    ends_at=self.duration,
                    winners=self.winners,
                    image_link=self.image_link,
                    message=giveaway_message,
                )
                pretty_log("info", "✅ Giveaway embed built successfully")
                view = GiveawayButtonsView(
                    bot=self.bot,
                    giveaway_type=self.giveaway_type,
                    giveaway_id=giveaway_id,
                    guild=self.channel.guild,
                )

                ga_msg = await self.channel.send(embed=ga_embed, view=view)
                content_msg = await self.channel.send(content=content)
                await interaction.followup.send(
                    "Giveaway created successfully!", ephemeral=True
                )
                view.message_id = (
                    ga_msg.id
                )  # Store message ID in the view for later use

                # Update giveaway record with message ID
                await update_giveaway_message_id(
                    bot=self.bot, giveaway_id=giveaway_id, message_id=ga_msg.id
                )
                # Make thread
                thread = await ga_msg.create_thread(
                    name=f"🎁 | ID: {giveaway_id}", auto_archive_duration=4320
                )
                thread_id = thread.id
                await update_giveaway_thread_id(
                    bot=self.bot, giveaway_id=giveaway_id, thread_id=thread_id
                )

            except Exception as e:
                await interaction.followup.send(
                    "An error occurred while building the giveaway embed.",
                    ephemeral=True,
                )
                pretty_log(
                    "error",
                    f"Error building giveaway embed in modal submission: {e}",
                )
                return

            # Create giveaway embed
        except Exception as e:
            pretty_log(
                "error",
                f"Error deferring response in modal submission: {e}",
            )
            return


# 🌸─────────────────────────────────────────
#       Giveaway Modal (Popup for Staff)
# 🌸─────────────────────────────────────────
async def create_giveaway_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int,
    giveaway_type: str,
    has_message: bool,
    host: discord.Member = None,
    image_link: str = None,
):
    """Handles the creation of a giveaway, including database operations and sending the giveaway message."""

    # Check if user has required roles to use the command
    user_roles = [role.id for role in interaction.user.roles]
    success, error_msg = await can_host_ga(interaction.user)
    if not success:
        await interaction.response.send_message(error_msg, ephemeral=True)
        return
    # Parse duration string
    try:
        total_duration = parse_total_duration(duration)
    except ValueError as e:
        await interaction.response.send_message(
            "Invalid duration format. Please use a format like '1d2h30m'.",
            ephemeral=True,
        )
        return

    channel_id = (
        VN_ALLSTARS_TEXT_CHANNELS.clan_giveaway
        if giveaway_type == "clan"
        else VN_ALLSTARS_TEXT_CHANNELS.giveaway
    )
    if TESTING_GA:
        channel_id = VN_ALLSTARS_TEXT_CHANNELS.khys_chamber

    channel = bot.get_channel(channel_id)
    if channel is None:
        await interaction.response.send_message(
            "An error occurred while fetching the giveaway channel. Please contact an administrator.",
            ephemeral=True,
        )
        pretty_log(
            "error",
            f"Channel with ID {channel_id} not found for giveaway creation.",
        )
        return
    host = interaction.user if host is None else host
    # Show the giveaway details modal to the user
    if has_message:
        modal = GiveawayDetailsModal(
            bot=bot,
            giveaway_type=giveaway_type,
            duration=total_duration,
            prize=prize,
            winners=winners,
            channel=channel,
            host=host,
            image_link=image_link,
        )
        await interaction.response.send_modal(modal)
        return
    # defer
    await interaction.response.defer(ephemeral=True)
    # If no message is needed, proceed to create giveaway immediately
    try:
        giveaway_id = await upsert_giveaway(
            bot=bot,
            message_id=0,  # Placeholder, will update after sending message
            host_id=host.id,
            host_name=host.display_name,
            giveaway_type=giveaway_type,
            prize=prize,
            ends_at=total_duration,
            max_winners=winners,
            channel_id=channel.id,
            image_link=image_link,
        )
    except Exception as e:
        await interaction.followup.send(
            "An error occurred while saving the giveaway to the database.",
            ephemeral=True,
        )
        pretty_log(
            "error",
            f"Error inserting giveaway into database in no-message giveaway creation: {e}",
        )
        return
    try:
        ga_embed, content = build_ga_embed(
            host=host,
            giveaway_type=giveaway_type,
            prize=prize,
            ends_at=total_duration,
            winners=winners,
            image_link=image_link,
        )
        pretty_log("info", "✅ Giveaway embed built successfully")
        view = GiveawayButtonsView(
            bot=bot,
            giveaway_type=giveaway_type,
            giveaway_id=giveaway_id,
            guild=channel.guild,
        )

        ga_msg = await channel.send(embed=ga_embed, view=view)
        await interaction.followup.send(
            "Giveaway created successfully!", ephemeral=True
        )
        view.message_id = ga_msg.id  # Store message ID in the view for later use

        # Update giveaway record with message ID
        await update_giveaway_message_id(
            bot=bot, giveaway_id=giveaway_id, message_id=ga_msg.id
        )
        # Make thread
        thread = await ga_msg.create_thread(
            name=f"🎁 | ID: {giveaway_id}", auto_archive_duration=4320
        )
        thread_id = thread.id
        await update_giveaway_thread_id(
            bot=bot, giveaway_id=giveaway_id, thread_id=thread_id
        )
    except Exception as e:
        await interaction.followup.send(
            "An error occurred while building the giveaway embed.",
            ephemeral=True,
        )
        pretty_log(
            "error",
            f"Error building giveaway embed in no-message giveaway creation: {e}",
        )
        return
