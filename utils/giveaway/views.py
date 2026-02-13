import time

import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from Constants.aesthetic import *
from Constants.giveaway import BLACKLISTED_ROLES, Extra_Entries
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    YUKI_USER_ID,
)
from utils.db.ga_db import (
    fetch_giveaway_id_by_message_id,
    fetch_giveaway_row_by_message_id,
    update_giveaway_message_id,
    update_giveaway_thread_id,
    upsert_giveaway,
)
from utils.db.ga_entry_db import (
    delete_ga_entry,
    fetch_entries_by_giveaway,
    fetch_ga_entry,
    upsert_ga_entry,
)
from utils.essentials.role_checks import *
from utils.giveaway.giveaway_funcs import (
    build_ga_embed,
    can_host_ga,
    compute_total_entries,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.parsers.duration import parse_total_duration
from utils.visuals.colors import get_random_ghouldengo_color
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer
from utils.visuals.thumbnails import random_ga_thumbnail_url

ITEMS_PER_PAGE = 25  # max participants per page


async def join_and_extra_entry(
    bot: discord.Client,
    interaction: discord.Interaction,
    giveaway_id: int,
    user: discord.Member,
    giveaway_type: str,
):
    """Handles a user joining a giveaway and calculates their total entries."""
    guild = user.guild

    is_clan_ga = giveaway_type == "clan"
    vna_member_role = guild.get_role(VN_ALLSTARS_ROLES.vna_member)
    if is_clan_ga and vna_member_role not in user.roles:
        await interaction.response.send_message(
            "❌ You do not have the required role to join this giveaway.",
            ephemeral=True,
        )

    # Check for blacklisted roles
    for blacklisted_role_id in BLACKLISTED_ROLES:
        blacklisted_role = guild.get_role(blacklisted_role_id)
        if blacklisted_role in user.roles:
            await interaction.response.send_message(
                f"❌ You are not allowed to join this giveaway, as you have the {blacklisted_role.mention} role.",
                ephemeral=True,
            )
            return
    # Calculate total entries
    total_entries, bonus_text = compute_total_entries(user)
    # Add entry to database
    await upsert_ga_entry(bot, giveaway_id, user.id, user.name, total_entries)
    await interaction.response.send_message(
        f"✅ You have successfully joined the giveaway with {total_entries} entries{bonus_text}!",
        ephemeral=True,
    )


# 🌸─────────────────────────────────────────
#     Ephemeral Paginated Participants View
# 🌸─────────────────────────────────────────
class ParticipantsPaginationView(discord.ui.View):
    def __init__(self, entries: list, guild: discord.Guild):
        super().__init__(timeout=120)
        self.entries = entries
        self.guild = guild
        self.current_page = 0
        self.max_page = max((len(entries) - 1) // ITEMS_PER_PAGE, 0)

        # Only add Prev/Next buttons if enough entries to paginate
        if len(entries) > ITEMS_PER_PAGE:
            prev_button = Button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
            prev_button.callback = self.prev_button_callback
            self.add_item(prev_button)

            next_button = Button(label="Next ➡️", style=discord.ButtonStyle.secondary)
            next_button.callback = self.next_button_callback
            self.add_item(next_button)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎁 Giveaway Participants",
            color=get_random_ghouldengo_color(),
        )
        embed.set_thumbnail(url=random_ga_thumbnail_url())
        # embed.set_image(url=DividerImages.Blue_Flower_3)
        if not self.entries:
            embed.description = "No participants yet 👀"
            return embed

        start_idx = self.current_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_entries = self.entries[start_idx:end_idx]

        lines = []
        for idx, entry in enumerate(page_entries, start=start_idx + 1):
            member = self.guild.get_member(entry["user_id"]) if self.guild else None
            if not member:
                continue
            total_entries = entry["entry_count"]  # Use exact DB value
            lines.append(f"{idx}. **{member.display_name}** — {total_entries} entries")

        embed.description = "\n".join(lines)
        total_participants = len(self.entries)
        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.max_page + 1} | {total_participants} total participants"
        )
        return embed

    async def prev_button_callback(self, interaction: discord.Interaction):
        try:
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(
                    embed=self.get_embed(), view=self
                )
            else:
                await interaction.response.send_message(
                    "You're on the first page!", ephemeral=True
                )
        except Exception as e:
            pretty_log("error", f"Prev button error: {e}")
            await interaction.response.send_message(
                f"❌ Error navigating pages: {e}", ephemeral=True
            )

    async def next_button_callback(self, interaction: discord.Interaction):
        try:
            if self.current_page < self.max_page:
                self.current_page += 1
                await interaction.response.edit_message(
                    embed=self.get_embed(), view=self
                )
            else:
                await interaction.response.send_message(
                    "You're on the last page!", ephemeral=True
                )
        except Exception as e:
            pretty_log("error", f"Next button error: {e}")
            await interaction.response.send_message(
                f"❌ Error navigating pages: {e}", ephemeral=True
            )


# 🌸─────────────────────────────────────────
#        Giveaway Buttons (Join + Participants)
# 🌸─────────────────────────────────────────
class GiveawayButtonsView(discord.ui.View):

    def __init__(
        self,
        bot: discord.Client,
        giveaway_type: str,
        giveaway_id: int = None,
        guild: discord.Guild = None,
        message_id: int = None,  # <--- add this
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.giveaway_type = giveaway_type
        self.giveaway_id = giveaway_id
        self.guild = guild
        self.message_id = message_id  # store it

    @discord.ui.button(
        label="Join",
        style=discord.ButtonStyle.primary,
        custom_id="giveaway_join",
        emoji="🎉",
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """🟢 Handle join button clicks with toggle and active check"""
        try:
            # Fetch giveaway to ensure it exists and is active
            giveaway_message_id = self.message_id
            giveaway_info = await fetch_giveaway_row_by_message_id(
                self.bot, giveaway_message_id
            )

            if not giveaway_info:
                await interaction.response.send_message(
                    "❌ This giveaway has already ended or is no longer active.",
                    ephemeral=True,
                )
                return
            # Get info
            giveaway_id = giveaway_info["giveaway_id"]
            giveaway_type = giveaway_info["giveaway_type"]

            # Check if user has joined already
            user_id = interaction.user.id
            entry_count = await fetch_ga_entry(self.bot, giveaway_id, user_id)
            if entry_count > 0:
                # User already joined → remove entry
                await delete_ga_entry(self.bot, giveaway_id, interaction.user.id)
                await interaction.response.send_message(
                    "✅ You have been removed from the giveaway.",
                    ephemeral=True,
                )
                pretty_log(
                    tag="giveaway",
                    message=f"🗑️ Removed {interaction.user.name}  from giveaway {self.giveaway_id}",
                )
            else:
                # User has not joined → add entry
                await join_and_extra_entry(
                    bot=self.bot,
                    interaction=interaction,
                    giveaway_id=giveaway_id,
                    user=interaction.user,
                    giveaway_type=giveaway_type,
                )
        except Exception as e:
            pretty_log(
                tag="giveaway",
                message=f"Error handling join button click: {e}",
                include_trace=True,
                level="error",
            )
            # Use followup if initial response might be done
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ An error occurred while joining the giveaway: {e}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"❌ An error occurred while joining the giveaway: {e}",
                    ephemeral=True,
                )

    @discord.ui.button(
        label="Participants",
        style=discord.ButtonStyle.secondary,
        custom_id="giveaway_participants",
        emoji="👥",
    )
    async def participants_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """👥 Show ephemeral paginated participant list"""
        try:
            giveaway_message_id = self.message_id
            giveaway = await fetch_giveaway_row_by_message_id(
                self.bot, giveaway_message_id
            )
            giveaway_id = giveaway.get("id")
            entries = await fetch_entries_by_giveaway(self.bot, giveaway_id)
            entries.sort(key=lambda x: x["joined_at"])
            if not entries:
                await interaction.response.send_message(
                    "No participants yet 👀", ephemeral=True
                )
                return

            # Open ephemeral pagination view
            view = ParticipantsPaginationView(entries=entries, guild=interaction.guild)
            await interaction.response.send_message(
                embed=view.get_embed(), view=view, ephemeral=True
            )
            pretty_log(
                "cmd",
                f"{interaction.user} opened Participants view",
            )

        except Exception as e:
            pretty_log(
                "error",
                f"Participants button error: {e}",
            )
            await interaction.response.send_message(
                f"❌ Error while fetching participants: {e}", ephemeral=True
            )
