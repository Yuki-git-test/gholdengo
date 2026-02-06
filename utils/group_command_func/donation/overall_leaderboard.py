from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import Button, View

from Constants.aesthetic import *
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VNA_SERVER_ID
from utils.db.donations_db import fetch_all_donation_records
from utils.essentials.format import format_comma_pokecoins
from utils.essentials.role_checks import *
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


class Donation_Leaderboard_Paginator(View):
    def __init__(self, bot, user: discord.Member, title, donation_records, per_page=25):
        super().__init__(timeout=120)  # No timeout for the view
        self.bot = bot
        self.user = user
        self.title = title
        self.donation_records = donation_records
        self.per_page = per_page
        self.page = 0
        self.max_page = (len(donation_records) - 1) // per_page
        self.message = None  # Store message reference for later editing

        # If there's only one page, remove the buttons
        if self.max_page == 0:
            self.clear_items()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this button.", ephemeral=True
            )
            return
        self.page -= 1
        if self.page < 0:
            self.page = self.max_page
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this button.", ephemeral=True
            )
            return
        self.page += 1
        if self.page > self.max_page:
            self.page = 0
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def get_embed(self):
        total_donators = len(self.donation_records)
        start = self.page * self.per_page
        end = start + self.per_page
        page_donators = self.donation_records[start:end]
        guild: discord.Guild = self.bot.get_guild(VNA_SERVER_ID)
        embed = discord.Embed(
            title=self.title,
            color=DEFAULT_EMBED_COLOR,
            timestamp=datetime.now(),
        )

        context = "Overall Donations" if "Overall" in self.title else "Monthly Donations"
        # Get user's rank in the leaderboard
        user_rank = None
        for idx, record in enumerate(self.donation_records):
            if record["user_id"] == self.user.id:
                user_rank = idx + 1
                user_donation = (
                    record["total_donations"]
                    if context == "Overall Donations"
                    else record["monthly_donations"]
                )
                user_donation_formatted = format_comma_pokecoins(user_donation)
                break
        description = ""
        if user_rank:
            description += f"Your current rank: **#{user_rank}** with {user_donation_formatted}\n\n"
        for index, record in enumerate(page_donators, start=start + 1):
            member_id = record["user_id"]
            member = guild.get_member(member_id)
            if not member:
                continue
            donation_amount = (
                record["total_donations"]
                if context == "Overall Donations"
                else record["monthly_donations"]
            )
            prefix = None
            if index == 1:
                prefix = "🥇 "
            elif index == 2:
                prefix = "🥈 "
            elif index == 3:
                prefix = "🥉 "
            else:
                prefix = f"{index}. "
            user_line = f"{prefix}**{member.display_name}**"
            donation_amount_formatted = format_comma_pokecoins(donation_amount)
            field_value = f"> - **{donation_amount_formatted}**"
            embed.add_field(name=user_line, value=field_value, inline=False)
        embed.set_footer(
            text=f"Total Donators: {total_donators} | Page {self.page + 1}/{self.max_page + 1}",
            icon_url=guild.icon.url if guild.icon else None,
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.description = description
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception as e:
                pass  # Message was deleted, nothing to do


async def view_overall_leaderboard(bot, interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction, content="Fetching leaderboard data...", ephemeral=False
    )
    donation_records = await fetch_all_donation_records(bot)
    if not donation_records:
        await loader.error(content="No donation records found.")
        return

    title = "🏆 Overall Donations Leaderboard 🏆"
    sorted_records = sorted(
        donation_records, key=lambda x: x["total_donations"], reverse=True
    )
    try:
        paginator = Donation_Leaderboard_Paginator(
            bot=bot,
            user=user,
            title=title,
            donation_records=sorted_records,
            per_page=25,
        )
        embed = await paginator.get_embed()
        sent_msg = await loader.success(
            content="",
            embed=embed,
            view=paginator,
        )
        paginator.message = sent_msg
    except Exception as e:
        await loader.error(
            content="An error occurred while generating the leaderboard."
        )
        pretty_log(
            message=f"❌ Error in view_overall_leaderboard: {e}",
            tag="error",
            include_trace=True,
        )
